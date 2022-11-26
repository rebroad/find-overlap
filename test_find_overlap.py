# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2022 Mike Fleetwood
# FILE: test_command_line.py

"""test_find_overlap.py

find-overlap.py command line argument parsing is tested by running this
as an executable so therefore requires the PATH environment variable to
be modified so that it can be found.  This script adds the current
directory to the start of the PATH to enable this, therefore run Pytest
like this:

    cd .../find-overlap
    python -m pytest
"""


import importlib
import io
import os
import subprocess

from collections import namedtuple


EXIT_SUCCESS = 0


find_overlap = None


def setup_module():
    """Extend PATH with current working directory to allow
    find-overlap.py executable to be found.  Manually import
    find-overlap module to avoid normal import failing because dash is
    not a valid character in a python identifier.
    """
    cwd = os.getcwd()
    path = os.environ['PATH']
    os.environ['PATH'] = cwd + os.pathsep + path
    global find_overlap
    if not find_overlap:
        find_overlap = importlib.import_module('find-overlap')


def test_command_line_help_option():
    """Test successful exit status and output includes 'help'"""
    out = subprocess.check_output(['find-overlap.py', '--help'])
    assert 'help' in out


def test_command_line_no_argument():
    rc = subprocess.call(['find-overlap.py'])
    assert rc == EXIT_SUCCESS


def test_command_line_one_argument():
    rc = subprocess.call(['find-overlap.py', '/dev/null'])
    assert rc == EXIT_SUCCESS


def test_command_line_two_arguments():
    rc = subprocess.call(['find-overlap.py', '/dev/null', '/dev/null'])
    assert rc != EXIT_SUCCESS


RESULT_MD5_HASHES = [b"\xb6\xd8\x1b6\nVr\xd8\x0c'C\x0f9\x15>,",
                     b"\xb6\xd8\x1b6\nVr\xd8\x0c'C\x0f9\x15>,",
                     b'Y\x07\x15\x90\t\x9d!\xddC\x98\x96Y#8\xbf\x95']
def test_read_hashes():
    """Test reading 2.5 MiB of binary zero produces the expected list of
    MD5 hashes
    """
    f = io.BytesIO(int(find_overlap.BLOCKSIZE * 2.5) * b'\x00')
    result = find_overlap.read_hashes(f)
    assert result == RESULT_MD5_HASHES


def test_generate_matching_hashes():
    """Test using result from test_read_hashes()"""
    result = find_overlap.generate_matching_hashes(RESULT_MD5_HASHES)
    assert result == {b"\xb6\xd8\x1b6\nVr\xd8\x0c'C\x0f9\x15>,": [0, 1],
                      b'Y\x07\x15\x90\t\x9d!\xddC\x98\x96Y#8\xbf\x95': [2]}


def test_eliminate_non_duplicates():
    test_dict = {'#0': [0],
                 '#1': [1, 2],
                 '#2': [3],
                 '#3': [4, 5, 6],
                 '#4': [7, 8, 9, 10],
                 '#5': [11, 12, 13, 14, 15]}
    result_dict = {'#1': [1, 2], '#3': [4, 5, 6], '#4': [7, 8, 9, 10]}
    find_overlap.eliminate_non_duplicates(test_dict)
    assert test_dict == result_dict


def test_compute_offset_blocks():
    test_dict = {'#0': [1, 8],
                 '#1': [10, 13],
                 '#2': [11, 14],
                 '#3': [12, 15],
                 '#4': [20, 21, 22],
                 '#5': [25, 26, 27, 28]}
    result = find_overlap.compute_offset_blocks(test_dict)
    assert result == {1: [20, 21, 25, 26, 27], 2: [20, 25, 26], 3: [10, 11, 12, 25], 7: [1]}


def test_find_start_matching_block():
    test_hashes = ['#0', '#0', '#0', '#0']
    assert find_overlap.find_start_matching_block(2, 1, test_hashes) == 0
    test_hashes = ['#0', '#1', '#2', '#1', '#2', '#3']
    assert find_overlap.find_start_matching_block(2, 2, test_hashes) == 1


def test_find_stop_matching_block():
    test_hashes = ['#0', '#0', '#0', '#0']
    assert find_overlap.find_stop_matching_block(1, 1, test_hashes) == 3
    test_hashes = ['#0', '#1', '#2', '#1', '#2', '#3']
    assert find_overlap.find_stop_matching_block(1, 2, test_hashes) == 3


def test_compute_candidate_ranges():
    md5_hashes = ['#0', '#1', '#2', '#3', '#1', '#2', '#3', '#7']
    offset_blocks = {3: [1, 2, 3]}
    Candidate = namedtuple('Candidate',
                           ['offset', 'start_block', 'stop_block', 'rank'])
    result = find_overlap.compute_candidate_ranges(offset_blocks, md5_hashes)
    assert result == [Candidate(offset=3, start_block=1, stop_block=4, rank=1.0)]
