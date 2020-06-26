import torch
from fairseq.models.bart import BARTModel

bart = BARTModel.from_pretrained(
    '/home/sihaoc/bart.large.xsum/',
    checkpoint_file='model.pt',
)

bart.cuda()
bart.eval()
bart.half()

_config = {
    "beam": 6,
    "lenpen": 1.0,
    "max_len_b": 60,
    "min_len": 10,
    "no_repeat_ngram_size": 3
}


def produce_summary(source_text):
    source_b = [source_text.rstrip()]
    hypothesis_b = bart.sample(source_b, **_config)

    return hypothesis_b[0]