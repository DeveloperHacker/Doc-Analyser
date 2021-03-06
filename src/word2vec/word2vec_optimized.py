# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Multi-threaded word2vec unbatched skip-gram model.

Trains the model described in:
(Mikolov, et. al.) Efficient Estimation of Word Representations in Vector Space
ICLR 2013.
http://arxiv.org/abs/1301.3781
This model does true SGD (i.e. no minibatching). To do this efficiently, custom
ops are used to sequentially process data within a 'batch'.

The key ops used are:
* skipgram custom op that does input processing.
* neg_train custom op that efficiently calculates and applies the gradient using
  true SGD.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import threading
import time

import tensorflow as tf

from logger import logger

word2vec = tf.load_op_library(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'word2vec_ops.so'))

flags = tf.app.flags

flags.DEFINE_string("save_path", None, "Directory to write the model.")
flags.DEFINE_string(
    "train_data", None,
    "Training data. E.g., unzipped file http://mattmahoney.net/dc/text8.zip.")
flags.DEFINE_string(
    "eval_data", None, "Analogy questions. "
                       "See README.md for how to get 'questions-words.txt'.")
flags.DEFINE_integer("embedding_size", 200, "The word2vec dimension size.")
flags.DEFINE_integer(
    "epochs_to_train", 15,
    "Number of epochs to train. Each epoch processes the training data once "
    "completely.")
flags.DEFINE_float("learning_rate", 0.025, "Initial learning rate.")
flags.DEFINE_integer("num_neg_samples", 25,
                     "Negative samples per training example.")
flags.DEFINE_integer("batch_size", 500,
                     "Numbers of training examples each step processes "
                     "(no minibatching).")
flags.DEFINE_integer("concurrent_steps", 12,
                     "The number of concurrent training steps.")
flags.DEFINE_integer("window_size", 5,
                     "The number of words to predict to the left and right "
                     "of the target word.")
flags.DEFINE_integer("min_count", 5,
                     "The minimum number of word occurrences for it to be "
                     "included in the vocabulary.")
flags.DEFINE_float("subsample", 1e-3,
                   "Subsample threshold for word occurrence. Words that appear "
                   "with higher frequency will be randomly down-sampled. Set "
                   "to 0 to disable.")
flags.DEFINE_boolean(
    "interactive", False,
    "If true, enters an IPython interactive session to play with the trained "
    "model. E.g., try model.analogy(b'france', b'paris', b'russia') and "
    "model.nearby([b'proton', b'elephant', b'maxwell'])")

FLAGS = flags.FLAGS


class Options(object):
    """Options used by our word2vec model."""

    def __init__(self):
        # Model options.

        # Embedding dimension.
        self.emb_dim = FLAGS.embedding_size

        # Training options.

        # The training text file.
        self.train_data = FLAGS.train_data

        # Number of negative samples per example.
        self.num_samples = FLAGS.num_neg_samples

        # The initial learning rate.
        self.learning_rate = FLAGS.learning_rate

        # Number of epochs to train. After these many epochs, the learning
        # rate decays linearly to zero and the training stops.
        self.epochs_to_train = FLAGS.epochs_to_train

        # Concurrent training steps.
        self.concurrent_steps = FLAGS.concurrent_steps

        # Number of examples for one training step.
        self.batch_size = FLAGS.batch_size

        # The number of words to predict to the left and right of the target word.
        self.window_size = FLAGS.window_size

        # The minimum number of word occurrences for it to be included in the
        # vocabulary.
        self.min_count = FLAGS.min_count

        # Subsampling threshold for word occurrence.
        self.subsample = FLAGS.subsample

        # Where to write out summaries.
        self.save_path = FLAGS.save_path
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

        # Eval options.

        # The text file for eval.
        self.eval_data = FLAGS.eval_data


class Word2Vec(object):
    """Word2Vec model (Skipgram)."""

    def __init__(self, options, session):
        self._options = options
        self._session = session
        self.word2id = {}
        self.id2word = []
        self.__build_graph()
        self.__save_vocab()

    def __build_graph(self):
        """Build the model graph."""
        opts = self._options

        # The training data. A text file.
        (words, counts, words_per_epoch, current_epoch, total_words_processed,
         examples, labels) = word2vec.skipgram_word2vec(filename=opts.train_data,
                                                        batch_size=opts.batch_size,
                                                        window_size=opts.window_size,
                                                        min_count=opts.min_count,
                                                        subsample=opts.subsample)
        (opts.vocab_words, opts.vocab_counts,
         opts.words_per_epoch) = self._session.run([words, counts, words_per_epoch])
        opts.vocab_size = len(opts.vocab_words)
        logger.info("Data file: {}".format(opts.train_data))
        logger.info("Vocab size: {} + UNK".format(opts.vocab_size - 1))
        logger.info("Words per epoch: {}".format(opts.words_per_epoch))

        self.id2word = opts.vocab_words
        for i, w in enumerate(self.id2word):
            self.word2id[w] = i

        # Declare all configurations we need.
        # Input words word2vec: [vocab_size, emb_dim]
        w_in = tf.Variable(
            tf.random_uniform(
                [opts.vocab_size,
                 opts.emb_dim], -0.5 / opts.emb_dim, 0.5 / opts.emb_dim),
            name="w_in")

        # Global step: scalar, i.e., shape [].
        w_out = tf.Variable(tf.zeros([opts.vocab_size, opts.emb_dim]), name="w_out")

        # Global step: []
        global_step = tf.Variable(0, name="global_step")

        # Linear learning rate decay.
        words_to_train = float(opts.words_per_epoch * opts.epochs_to_train)
        lr = opts.learning_rate * tf.maximum(
            0.0001,
            1.0 - tf.cast(total_words_processed, tf.float32) / words_to_train)

        # Training nodes.
        inc = global_step.assign_add(1)
        with tf.control_dependencies([inc]):
            train = word2vec.neg_train_word2vec(w_in,
                                                w_out,
                                                examples,
                                                labels,
                                                lr,
                                                vocab_count=opts.vocab_counts.tolist(),
                                                num_negative_samples=opts.num_samples)

        self.w_in = w_in
        self._w_out = w_out
        self._examples = examples
        self._labels = labels
        self._lr = lr
        self._train = train
        self._global_step = global_step
        self._epoch = current_epoch
        self._words = total_words_processed
        self.saver = tf.train.Saver()
        tf.global_variables_initializer().run()

    def __save_vocab(self):
        """Save the vocabulary to a file so the model can be reloaded."""
        opts = self._options
        with open(os.path.join(opts.save_path, "vocab.txt"), "w") as f:
            for i in range(opts.vocab_size):
                vocab_word = tf.compat.as_text(opts.vocab_words[i]).encode("utf-8")
                f.write("%s %d\n" % (vocab_word,
                                     opts.vocab_counts[i]))

    def __train_thread_body(self):
        initial_epoch, = self._session.run([self._epoch])
        while True:
            _, epoch = self._session.run([self._train, self._epoch])
            if epoch != initial_epoch:
                break

    def train(self):
        """Train the model."""
        opts = self._options

        initial_epoch, initial_words = self._session.run([self._epoch, self._words])

        workers = []
        for _ in range(opts.concurrent_steps):
            t = threading.Thread(target=self.__train_thread_body)
            t.start()
            workers.append(t)

        last_words, last_time = initial_words, time.time()
        while True:
            time.sleep(5)  # Reports our progress once a while.
            (epoch, step, words, lr) = self._session.run(
                [self._epoch, self._global_step, self._words, self._lr])
            now = time.time()
            last_words, last_time, rate = words, now, (words - last_words) / (
                now - last_time)
            logger.info("Epoch %4d Step %8d: lr = %5.3f words/sec = %8.0f" % (epoch, step, lr, rate))
            sys.stdout.flush()
            if epoch != initial_epoch:
                break

        for t in workers:
            t.join()
