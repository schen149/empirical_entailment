from transformers import PreTrainedModel, PreTrainedTokenizer, AutoModelForSeq2SeqLM, AutoTokenizer, GPT2LMHeadModel, GPT2Tokenizer
from typing import Optional, Tuple, List
from fairseq.models import BaseFairseqModel
from .entailment_model import calculate_entailment_score
import torch

import sys
import os
import importlib.util

_spec = importlib.util.spec_from_file_location("decode", os.path.abspath(os.path.join('..', 'entailment', 'decode.py')))
_decoder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_decoder)

np_constrained_spec = importlib.util.spec_from_file_location("np_decode", os.path.abspath(os.path.join('..', 'entailment', 'np_constrained_decode.py')))
np_constrained_decoder = importlib.util.module_from_spec(np_constrained_spec)
np_constrained_spec.loader.exec_module(np_constrained_decoder)

DEFAULT_CONFIG = {
    "num_beams": 6,
    "no_repeat_ngram_size": 3,
    "early_stopping": False,
    "min_length": 10,
    "max_length": 60,
    "do_sample": True,
}


def produce_summary_huggingface(source_text: str,
                               model: PreTrainedModel,
                               tokenizer: PreTrainedTokenizer,
                               config: Optional[dict] = None) -> List[Tuple[str, float]]:
    """
    Generates a summary using a model (huggingface's transformers library implementation).
    :param source_text: Source text/paragraph to produce summary on
    :param model: Pretrained transformer model
    :param tokenizer: corresponding tokenizer used for the model
    :param config: Configuration for generation/decoding.
    :return: Produced summary by the model
    """

    if not config:
        config = DEFAULT_CONFIG

    input_ids = torch.tensor(tokenizer.encode(source_text, add_special_tokens=True)).unsqueeze(0)
    input_ids = input_ids.to('cuda')
    generated = model.generate(input_ids, **config)
    gen_text_batch = tokenizer.batch_decode(
        generated, skip_special_tokens=True, clean_up_tokenization_spaces=True
    )

    return _evaluate_entailment_score(source_text=source_text,
                                      summary_candidates=gen_text_batch)


def produce_summary_huggingface_custom_decoding(source_text: str,
                                                model: PreTrainedModel,
                                                tokenizer: PreTrainedTokenizer,
                                                config: Optional[dict] = None) -> List[Tuple[str, float]]:
    """
    Generates a summary with custom decoding algorithm on a model (huggingface's transformers library implementation).
    :param source_text: Source text/paragraph to produce summary on
    :param model: Pretrained transformer model
    :param tokenizer: corresponding tokenizer used for the model
    :param config: Configuration for generation/decoding.
    :return: Produced summary by the model
    """

    if not config:
        config = DEFAULT_CONFIG

    input_ids = torch.tensor(tokenizer.encode(source_text, add_special_tokens=True))

    input_ids = input_ids.unsqueeze(0)

    input_ids = input_ids.to('cuda')

    generated = _decoder.decode(model=model,
                                input_ids=input_ids,
                                source_text=source_text,
                                tokenizer=tokenizer,
                                **config)

    gen_text_batch = tokenizer.batch_decode(
        generated, skip_special_tokens=True, clean_up_tokenization_spaces=True
    )

    return _evaluate_entailment_score(source_text=source_text,
                                      summary_candidates=gen_text_batch)


def produce_summary_np_constrained_decoding(source_text: str,
                                            model: PreTrainedModel,
                                            tokenizer: PreTrainedTokenizer,
                                            config: Optional[dict] = None) -> List[Tuple[str, float]]:
    """
    Generates a summary with np constrained decoding
    :param source_text: Source text/paragraph to produce summary on
    :param model: Pretrained transformer model
    :param tokenizer: corresponding tokenizer used for the model
    :param config: Configuration for generation/decoding.
    :return: Produced summary by the model
    """

    if not config:
        config = DEFAULT_CONFIG

    input_ids = torch.tensor(tokenizer.encode(source_text, add_special_tokens=True))
    input_ids = input_ids.unsqueeze(0)
    input_ids = input_ids.to('cuda')

    all_np_toks = np_constrained_decoder.get_tokenized_noun_phrases(source_text, tokenizer)

    all_summaries = []

    for np_toks in all_np_toks:
        generated = np_constrained_decoder.np_constrained_decode(model=model,
                                                                 input_ids=input_ids,
                                                                 prepend_decoded_token_ids=np_toks,
                                                                 **config)

        gen_text_batch = tokenizer.batch_decode(
            generated, skip_special_tokens=True, clean_up_tokenization_spaces=True
        )

        all_summaries.append(gen_text_batch[0])

    return _evaluate_entailment_score(source_text=source_text,
                                      summary_candidates=all_summaries)


def load_model_and_tokenizer_huggingface(model_name_or_dir: str) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
    """
    Downloads/Loads a pretrained huggingface model and tokenizer.
    :param model_name_or_dir: Directory or the name of the model. See https://huggingface.co/ for the complete list
    :return: Pretrained model + tokenizer instance
    """
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name_or_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_dir)
    return model, tokenizer


def load_gpt2(model_name_or_dir: str) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
    model = GPT2LMHeadModel.from_pretrained(model_name_or_dir)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name_or_dir)
    return model, tokenizer


def produce_summary_fairseq(source_text: str,
                            model: BaseFairseqModel,
                            config: dict) -> str:
    """
    Generates a summary with a pretrained fairseq model.
    TODO: need to connect entailment model to this
    :param source_text: Source text/paragraph to produce summary on
    :param model: Pretrained fairseq model
    :param config: Configuration for generation/decoding.
    :return: Produced summary by the model
    """
    source_b = [source_text.rstrip()]
    hypothesis_b = model.sample(source_b, **config)

    return hypothesis_b[0]


def _evaluate_entailment_score(source_text: str,
                               summary_candidates: List[str]) -> List[Tuple[str, float]]:
    source_text_batch = [source_text] * len(summary_candidates)
    entailment_score = calculate_entailment_score(source_text_batch, summary_candidates)
    entailment_score = entailment_score.tolist()
    res = list(zip(summary_candidates, entailment_score))
    return res