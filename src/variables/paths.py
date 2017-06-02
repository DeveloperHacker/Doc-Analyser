RESOURCES = "resources"

DATA_SETS = RESOURCES + "/data-sets"
SENTENCES = DATA_SETS + "/sentences.txt"
FILTERED = DATA_SETS + "/filtered.txt"
# BATCHES = DATA_SETS + "/batches.pickle"
METHODS = DATA_SETS + "/methods.xml"
VEC_METHODS = DATA_SETS + "/methods.pickle"
EMBEDDINGS = DATA_SETS + "/embeddings.pickle"
CONTEXTS = DATA_SETS + "/contexts.pickle"
PRETRAIN_SETS = DATA_SETS + "/pretrain_sets"

NETS = RESOURCES + "/nets"

WORD2VEC = NETS + "/word2vec"
WORD2VEC_MODEL = WORD2VEC + "/model.ckpt"
WORD2VEC_LOG = WORD2VEC + "/word2vec.log"

SEQ2SEQ = NETS + "/seq2seq"
ANALYSER_LOG = SEQ2SEQ + "/analyser.log"
Q_FUNCTION_LOG = SEQ2SEQ + "/q-function.log"
CONTRACTS_LOG = SEQ2SEQ + "/contracts.log"
GENERATOR_LOG = SEQ2SEQ + "/generator.log"
BATCHES = SEQ2SEQ + "/batches"
ANALYSER_BATCHES = BATCHES + "/analyser-batches.pickle"
Q_FUNCTION_BATCHES = BATCHES + "/q-function-batches.pickle"
MUNCHHAUSEN_PRETRAIN_SET = BATCHES + "/munchhausen-pretrain-set.pickle"
MUNCHHAUSEN_TRAIN_SET = BATCHES + "/munchhausen-train-set.pickle"
MUNCHHAUSEN_LOG = SEQ2SEQ + "/munchhausen.log"

ANALYSER = RESOURCES + "/analyser"
ANALYSER_RAW_METHODS = ANALYSER + "/methods.xml"
ANALYSER_METHODS = ANALYSER + "/methods.pickle"
ANALYSER_DATA_SET = ANALYSER + "/data_set.pickle"
ANALYSER_TRAIN_LOG = ANALYSER + "/train.log"
ANALYSER_TEST_LOG = ANALYSER + "/test.log"
ANALYSER_PREPARE_DATA_SET_LOG = ANALYSER + "/prepare.log"
ANALYSER_GRAPH = ANALYSER + "/loss.png"
