import math
import random
import time
import sys

import numpy

TOKEN_LENGTH = 11


def compare_token(got, expected):
    """An example of a non-timing-invariant comparison function.

    Python's built-in string comparison function isn't quite this egregious, but it's close.
    """
    if len(got) != len(expected):
        return False
    for i in xrange(len(got)):
        if got[i] != expected[i]:
            return False
    return True


expected = [random.choice(range(10)) for i in range(TOKEN_LENGTH)]

print "This program isn't perfect, but it will often guess the random token using nothing more than a bad comparison function."
print "Token is %s" % ''.join(map(str, expected))


def guess_and_time(init_guess):
    times = []
    tofill = range(TOKEN_LENGTH - len(init_guess))
    # TODO: pick this number based on the standard deviation
    for i in xrange(2000000):
        # fill with rotating data to avoid biasing the results
        guess = init_guess + [i % 10 for _ in tofill]
        start = time.time()
        compare_token(guess, expected)
        end = time.time()
        times.append(end - start)
    return numpy.mean(times), numpy.std(times) / math.sqrt(len(times))


def main():
    overall_guess = []

    for character in xrange(TOKEN_LENGTH):
        sys.stdout.write("> ")
        sys.stdout.flush()
        all_times = []
        for digit in range(10):
            guess = overall_guess + [digit]
            time, std = guess_and_time(guess)
            all_times.append((digit, time, std))
            sys.stdout.write(". ")
            sys.stdout.flush()
        sys.stdout.write("\n")

        average_time = numpy.mean([t[1] for t in all_times])
        all_times.sort(key=lambda (d, t, s): t - average_time, reverse=True)
        digit, time, stderr = all_times[0]
        delta = time - average_time
        print "Guessing %d (%s, %s, %f)" % (digit, delta, stderr, delta / stderr)
        overall_guess.append(digit)
    print "I think the token is %s" % ''.join(map(str, overall_guess))


if __name__ == '__main__':
    main()
