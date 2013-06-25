import gc
import math
import numpy
import optparse
import random
import sys
import time


def compare_character(got, expected):
    return ord(unichr(got)) == ord(unichr(expected))


def compare_token(got, expected):
    """An example of a non-timing-invariant comparison function.

    Python's built-in string comparison function isn't quite this egregious, but it's close.
    """
    if len(got) != len(expected):
        return False
    for i in xrange(len(got)):
        if not compare_character(got[i], expected[i]):
            return False
    return True


def guess_and_time(init_guess, expected, iterations, token_length):
    tofill = range(token_length - len(init_guess))
    # do a collection before we start to try and reduce variance inside the
    # loop
    gc.collect()
    # algorithm for running variance copied from
    # http://www.johndcook.com/standard_deviation.html,
    # originally from B. P. Welford
    m_N = 0
    prev_M = 0
    next_M = 0
    prev_S = 0
    next_S = 0
    for i in xrange(iterations):
        m_N += 1
        # fill with rotating data to avoid biasing the results
        guess = init_guess + [i % 10 for _ in tofill]
        start = time.time()
        compare_token(guess, expected)
        end = time.time()
        this_time = (1000000.0 * (end - start))

        if (m_N == 1):
            prev_M = next_M = this_time
            prev_S = 0.0
        else:
            next_M = prev_M + (this_time - prev_M) / m_N
            next_S = prev_S + (this_time - prev_M) * (this_time - next_M)
            prev_M = next_M
            prev_S = next_S

    return next_M, math.sqrt(next_S / (m_N - 1))


def main():
    parser = optparse.OptionParser()
    parser.add_option('-i', '--iterations', default=5000000, type=int, help='Number of iterations to run for (default %default)')
    parser.add_option('-c', '--confidence-threshold', default=0.2, type=float, help='How to low to get confidence get before aborting (default %default)')
    parser.add_option('-t', '--token-length', default=5, type=int, help='How long to make the token (default %default, ignored if you pass --token)')
    parser.add_option('--token', default=None, type=str, help='The token to use (default: randomly generated)')
    opts, args = parser.parse_args()

    if opts.token is not None:
        expected = map(int, opts.token.split())
    else:
        expected = [random.choice(range(10)) for i in range(opts.token_length)]

    token_length = len(expected)

    print "This program isn't perfect, but it will often guess the random token using nothing more than a bad comparison function."
    print "Token is %s" % ''.join(map(str, expected))

    overall_guess = []

    for character in xrange(token_length):
        sys.stdout.write("> ")
        sys.stdout.flush()
        all_times = []
        for digit in range(10):
            guess = overall_guess + [digit]
            time, std = guess_and_time(guess, expected, opts.iterations, token_length)
            all_times.append((digit, time, std))
            sys.stdout.write(". ")
            sys.stdout.flush()
        sys.stdout.write("\n")

        print all_times
        average_time = numpy.mean([t[1] for t in all_times])
        all_times.sort(key=lambda (d, t, s): t - average_time, reverse=True)
        digit, time, stdev = all_times[0]
        delta = time - average_time
        # how many standard deviations away are we?
        confidence = delta / stdev
        print "Will guess %d (in %.1f +/- %0.1f micros, average %.1f micros cf=%f)" % (digit, time, stdev, average_time, confidence)
        if confidence < opts.confidence_threshold:
            print "Confidence too low, aborting"
            break
        overall_guess.append(digit)
    print "I think the token is %s%s" % (''.join(map(str, overall_guess)), ''.join('?' for _ in xrange(token_length - len(overall_guess))))


if __name__ == '__main__':
    main()
