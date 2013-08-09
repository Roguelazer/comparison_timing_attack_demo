This is a little demo of why it's bad to use non-constant-time string comparison functions in security-sensitive code.

The demo is pretty sensitive to system load if you want to be able to run it in a reasonable amount of time. On a very quiet system,
you can usually get good results by running with `-i 100`. On an interactive system with lots of interrupts, you need to increase
that by a few orders of magnitude to get reliable results.

It uses numpy and scipy, and should run on python 2.6, 2.7, or 3.3
