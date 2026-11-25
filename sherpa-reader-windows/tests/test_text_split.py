import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from main import split_sentences


def test_chinese_and_english_sentence_boundaries():
    assert split_sentences('你好。Hello! 下一句？') == ['你好。', 'Hello!', '下一句？']


def test_newline_boundaries_and_empty_lines():
    assert split_sentences('第一行\n\nSecond line.') == ['第一行', 'Second line.']


def test_mixed_text_order_is_preserved():
    parts = split_sentences('中文 English。第二句.')
    assert parts == ['中文 English。', '第二句.']
