from __future__ import print_function

import collections
import gc
import hashlib
import itertools
import numpy
import optparse
import operator
import random
import sys

import scipy.stats

MIN_AUTO_ITERATIONS = 20
MAX_AUTO_ITERATIONS = 10240

try:
    import time33
    timer = time33.perf_counter
except:
    import time
    try:
        timer = time.perf_counter
    except:
        if sys.platform == 'darwin' or sys.platform == 'win32':
            timer = time.clock  # time.clock is oddly-low-resolution on linux
        else:
            timer = time.time


def compare_character(got, expected):
    return got == expected


def compare_token(got, expected):
    """An example of a non-timing-invariant comparison function.

    Python's built-in string comparison function isn't quite this egregious, but it's close.
    """
    if len(got) != len(expected):
        return False
    for i in range(len(got)):
        if not compare_character(got[i], expected[i]):
            return False
    # just to be extra sure, also compare the hashes (yes, we're cheating
    # here to make it easier to guess the last character)
    got_enc = (''.join(got)).encode('utf-8')
    expected_enc = (''.join(expected)).encode('utf-8')
    return hashlib.sha1(got_enc).digest() == hashlib.sha1(expected_enc).digest()


def guess_and_time(init_guess, expected, iterations, token_length):
    tofill = range(token_length - len(init_guess))
    # do a collection before we start to try and reduce variance inside the
    # loop
    results = numpy.zeros(iterations)
    gc.collect()
    gc.disable()
    for i in range(iterations):
        # fill with rotating data to avoid biasing the results
        guess = init_guess + [i % 10 for _ in tofill]
        start = timer()
        compare_token(guess, expected)
        end = timer()
        this_time = (1000000.0 * (end - start))
        results[i] = this_time
    gc.enable()
    gc.collect()

    return results


def main():
    parser = optparse.OptionParser()
    parser.add_option('-i', '--iterations', default=None, type=int, help='Number of iterations to run for (if not passed, will be AUTOMAGIC)')
    parser.add_option('-c', '--confidence-threshold', default=0.02, type=float, help='Require p < CONFIDENCE_THRESHOLD for a digit (default %default)')
    parser.add_option('-t', '--token-length', default=5, type=int, help='How long to make the token (default %default, ignored if you pass --token)')
    parser.add_option('-v', '--verbose', action='store_true', help='Be verbose')
    parser.add_option('-n', '--numeric', default=False, action='store_true', help='Only generate numeric tokens')
    parser.add_option('-T', '--token', default=None, help='Token (for advanced use)')
    opts, args = parser.parse_args()

    if opts.numeric:
        language = list(map(str, range(10)))
    else:
        language = list(map(chr, list(range(ord('a'), ord('z')+1)) + list(range(ord('A'), ord('Z') + 1)) + list(range(ord('0'), ord('9') + 1))))
    if opts.token:
        expected = opts.token
    else:
        expected = [random.choice(language) for i in range(opts.token_length)]

    token_length = len(expected)

    print("This program isn't perfect, but it will often guess the random token using nothing more than a bad comparison function.")
    print("Token is %s" % ''.join(map(str, expected)))

    overall_guess = []

    Candidate = collections.namedtuple('Candidate', ['digit', 'mean', 'times', 'stddev'])
    Result = collections.namedtuple('Result', ['digit', 'mean', 'p_value', 'stddev'])
    FinalResult = collections.namedtuple('FinalResult', ['digit', 'mean', 'p_values', 'stddev'])

    last_iterations = None
    for character in range(token_length):
        sys.stdout.flush()
        if opts.iterations is not None:
            min_iterations = last_iterations or opts.iterations
            max_iterations = opts.iterations
        else:
            min_iterations = last_iterations or MIN_AUTO_ITERATIONS
            max_iterations = MAX_AUTO_ITERATIONS
        iterations = min_iterations
        candidates = []
        p_candidates = []
        while iterations <= max_iterations:
            sys.stdout.write("> (iterations=%d) " % iterations)
            all_times = []
            for digit in language:
                guess = overall_guess + [digit]
                times = guess_and_time(guess, expected, iterations, token_length)
                time = numpy.mean(times)
                all_times.append((digit, time, times))
                sys.stdout.write(". ")
                sys.stdout.flush()
            sys.stdout.write("\n")

            all_data = numpy.zeros(len(all_times) * iterations)
            for i, (_, __, times) in enumerate(all_times):
                for j, v in enumerate(times):
                    all_data[i*iterations + j] = v

            average_time = numpy.mean([t[1] for t in all_times])
            for digit, mean, times in all_times:
                std = numpy.std(times)
                candidates.append(Candidate(digit, mean, times, std))
            failed = []
            # Find all of the digits that are stastically different using
            # t-tests
            # XXX WARNING XXX: Doing paired t-tests like this isn't exactly the
            # best way to accomplish this
            for result1, result2 in itertools.product(candidates, candidates):
                if result1.digit == result2.digit:
                    continue
                t_value, p_value = scipy.stats.ttest_ind(result1.times, result2.times, equal_var=False)
                if p_value < opts.confidence_threshold:
                    p_candidates.append(Result(result1.digit, result1.mean, p_value, result1.stddev))
                    p_candidates.append(Result(result2.digit, result2.mean, p_value, result2.stddev))
                else:
                    failed.append(Result(result1.digit, result1.mean, p_value, result1.stddev))
            if p_candidates:
                last_iterations = iterations
                break
            if not p_candidates:
                print("No candidates were under confidence threshold %f (best %f)" % (opts.confidence_threshold, min(p.p_value for p in failed)))
                print("Retrying with higher iteration count")
                iterations *= 2
        if not p_candidates:
            print("No candidates found under confidence threshold %f, exhauted iterations" % opts.confidence_threshold)
            break
        # Now find the most common
        counts = dict((d, len([p for p in p_candidates if p.digit == d])) for d in language)
        most_common = max(counts.values())
        final_candidates_digits = [d for (d, c) in counts.items() if c == most_common]
        results = []
        for d in final_candidates_digits:
            p_values = [p.p_value for p in p_candidates if p.digit == d]
            candidate_entry = [c for c in candidates if c.digit == d][0]
            results.append(FinalResult(digit=candidate_entry.digit, mean=candidate_entry.mean, p_values=p_values, stddev=candidate_entry.stddev))
        results.sort(key=operator.attrgetter('mean'), reverse=True)
        if opts.verbose:
            print(results)
        digit, mean, p_values, std = results[0]
        print("Will guess %s (in %.1f +/- %0.1f micros, average %.1f micros, max_p_value=%f)" % (digit, mean, std, average_time, max(p_values)))
        overall_guess.append(digit)
    print("I think the token is %s%s" % (''.join(map(str, overall_guess)), ''.join('?' for _ in range(token_length - len(overall_guess)))))


if __name__ == '__main__':
    main()
