"""Tests for InVideoQuizXBlock views and field parsing."""

import json
from unittest.mock import Mock

from invideoquiz.invideoquiz import (
    InVideoQuizXBlock,
    parse_jump_back_field,
    parse_timemap_field,
)
from xblock.runtime import DictKeyValueStore, KvsFieldData
from xblock.test.tools import TestRuntime as Runtime


def _make_block(**field_values):
    key_store = DictKeyValueStore()
    field_data = KvsFieldData(key_store)
    runtime = Runtime(services={'field-data': field_data})
    runtime.local_resource_url = Mock(return_value='/static/test-resource')
    block = InVideoQuizXBlock(runtime, scope_ids=Mock())
    for key, value in field_values.items():
        setattr(block, key, value)
    return block


def test_invideoquiz_model_defaults():
    """Default field values match expected legacy defaults."""
    block = _make_block()
    assert block.display_name == 'In-Video Quiz XBlock'
    assert block.timemap == '{}'
    assert block.video_id == ''
    assert block.jump_back == ''


class TestParseTimemapField:
    def test_empty_returns_empty_dict(self):
        assert parse_timemap_field('') == {}
        assert parse_timemap_field(None) == {}

    def test_legacy_single_problem(self):
        raw = '{"1:30": "problem-1", "2:00": "problem-2"}'
        assert parse_timemap_field(raw) == {
            '1:30': 'problem-1',
            '2:00': 'problem-2',
        }

    def test_multi_problem_array_at_same_timestamp(self):
        raw = '{"1:30": ["problem-1", "problem-2"]}'
        assert parse_timemap_field(raw) == {
            '1:30': ['problem-1', 'problem-2'],
        }

    def test_invalid_json_returns_empty_dict(self):
        assert parse_timemap_field('not-json') == {}


class TestParseJumpBackField:
    def test_empty_returns_empty_dict(self):
        assert parse_jump_back_field('') == {}
        assert parse_jump_back_field(None) == {}

    def test_legacy_global_mm_ss_string(self):
        assert parse_jump_back_field('1:29') == '1:29'

    def test_legacy_time_keyed_map(self):
        raw = '{"1:30": "1:29", "2:00": "1:45"}'
        assert parse_jump_back_field(raw) == {
            '1:30': '1:29',
            '2:00': '1:45',
        }

    def test_per_problem_map(self):
        raw = '{"problem-1": "1:29", "problem-2": "1:45"}'
        assert parse_jump_back_field(raw) == {
            'problem-1': '1:29',
            'problem-2': '1:45',
        }

    def test_json_encoded_string_value(self):
        assert parse_jump_back_field('"1:29"') == '1:29'


class TestStudentViewConfig:
    @staticmethod
    def _config_javascript(fragment):
        return fragment.foot_html()

    def test_config_includes_legacy_timemap_and_per_problem_jump_back(self):
        block = _make_block(
            video_id='video-123',
            timemap='{"1:30": ["problem-1", "problem-2"]}',
            jump_back='{"problem-1": "1:29", "problem-2": "1:45"}',
        )
        fragment = block.student_view()
        javascript = self._config_javascript(fragment)
        assert 'video-123' in javascript
        assert 'problem-1' in javascript
        assert '1:45' in javascript
        assert '1:30' in javascript

    def test_config_supports_legacy_global_jump_back_string(self):
        block = _make_block(
            video_id='video-abc',
            timemap='{"1:30": "problem-1"}',
            jump_back='1:29',
        )
        fragment = block.student_view()
        javascript = self._config_javascript(fragment)
        assert 'jumpBack' in javascript
        assert '1:29' in javascript

    def test_config_handles_empty_jump_back(self):
        block = _make_block(
            video_id='video-abc',
            timemap='{"1:30": "problem-1"}',
            jump_back='',
        )
        fragment = block.student_view()
        javascript = self._config_javascript(fragment)
        assert 'jumpBack' in javascript
        assert 'timemap' in javascript

    def test_config_timemap_is_valid_json_object_literal(self):
        block = _make_block(
            video_id='video-xyz',
            timemap='{"1:30": ["a", "b"]}',
            jump_back='{}',
        )
        fragment = block.student_view()
        javascript = self._config_javascript(fragment)
        timemap_line = next(
            line for line in javascript.splitlines() if 'timemap:' in line
        )
        timemap_json = timemap_line.split('timemap:', 1)[1].strip().rstrip(',')
        parsed = json.loads(timemap_json)
        assert parsed == {'1:30': ['a', 'b']}
