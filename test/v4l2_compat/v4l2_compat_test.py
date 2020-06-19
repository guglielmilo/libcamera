#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2020, Google Inc.
#
# Author: Paul Elder <paul.elder@ideasonboard.com>
#
# v4l2_compat_test.py - Test the V4L2 compatibility layer

import argparse
import glob
import os
import re
import shutil
import signal
import subprocess
import sys

TestPass = 0
TestFail = -1
TestSkip = 77


supported_pipelines = [
    'bcm2835-isp',
    'uvcvideo',
    'vimc',
]


def grep(exp, arr):
    return [s for s in arr if re.search(exp, s)]


def run_with_stdout(*args, env={}):
    try:
        with open(os.devnull, 'w') as devnull:
            output = subprocess.check_output(args, env=env, stderr=devnull)
        ret = 0
    except subprocess.CalledProcessError as err:
        output = err.output
        ret = err.returncode
    return ret, output.decode('utf-8').split('\n')


def extract_result(result):
    res = result.split(', ')
    ret = {}
    ret['total']     = int(res[0].split(': ')[-1])
    ret['succeeded'] = int(res[1].split(': ')[-1])
    ret['failed']    = int(res[2].split(': ')[-1])
    ret['warnings']  = int(res[3].split(': ')[-1])
    ret['device']    = res[0].split()[4].strip(':')
    ret['driver']    = res[0].split()[2]
    return ret


def print_output_arr(output_arr):
    print('\n'.join(output_arr))


def test_v4l2_compliance(v4l2_compliance, v4l2_compat, device, base_driver):
    ret, output = run_with_stdout(v4l2_compliance, '-s', '-d', device, env={'LD_PRELOAD': v4l2_compat})
    if ret < 0:
        print_output_arr(output)
        print(f'Test for {device} terminated due to signal {signal.Signals(-ret).name}')
        return TestFail

    result = extract_result(output[-2])
    if result['failed'] == 0:
        return TestPass

    # vimc will fail s_fmt because it only supports framesizes that are
    # multiples of 3
    if base_driver == 'vimc' and result['failed'] == 1:
        failures = grep('fail', output)
        if re.search('S_FMT cannot handle an invalid format', failures[0]) is None:
            print_output_arr(output)
            return TestFail
        return TestPass

    print_output_arr(output)
    return TestFail


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--all', action='store_true',
                        help='Test all available cameras')
    parser.add_argument('v4l2_compat', type=str,
                        help='Path to v4l2-compat.so')
    args = parser.parse_args(argv[1:])

    v4l2_compat = args.v4l2_compat

    v4l2_compliance = shutil.which('v4l2-compliance')
    if v4l2_compliance is None:
        print('v4l2-compliance is not available')
        return TestSkip

    v4l2_ctl = shutil.which('v4l2-ctl')
    if v4l2_ctl is None:
        print('v4l2-ctl is not available')
        return TestSkip

    dev_nodes = glob.glob('/dev/video*')
    if len(dev_nodes) == 0:
        print('no video nodes available to test with')
        return TestSkip

    failed = []
    drivers_tested = {}
    for device in dev_nodes:
        ret, out = run_with_stdout(v4l2_ctl, '-D', '-d', device, env={'LD_PRELOAD': v4l2_compat})
        if ret < 0:
            failed.append(device)
            print(f'v4l2-ctl failed on {device} with v4l2-compat')
            continue
        driver = grep('Driver name', out)[0].split(':')[-1].strip()
        if driver != "libcamera":
            continue

        ret, out = run_with_stdout(v4l2_ctl, '-D', '-d', device)
        if ret < 0:
            failed.append(device)
            print(f'v4l2-ctl failed on {device} without v4l2-compat')
            continue
        driver = grep('Driver name', out)[0].split(':')[-1].strip()
        if driver not in supported_pipelines:
            continue

        if not args.all and driver in drivers_tested:
            continue

        print(f'Testing {device} with {driver} driver... ', end='')
        ret = test_v4l2_compliance(v4l2_compliance, v4l2_compat, device, driver)
        if ret == TestFail:
            failed.append(device)
            print('failed')
        else:
            print('success')
        drivers_tested[driver] = True

    if len(failed) > 0:
        print(f'Failed {len(failed)} tests:')
        for device in failed:
            print(f'- {device}')

    return TestPass if not failed else TestFail


if __name__ == '__main__':
    sys.exit(main(sys.argv))