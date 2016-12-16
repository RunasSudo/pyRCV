#!/bin/zsh

echo WrightTalley
for i in {1..10}; do TIMEFMT="$i, %E"; time python2 WrightTalleyCSM8.py > /dev/null; done

echo pyRCV
for i in {1..10}; do TIMEFMT="$i, %E"; time python3 ../wright_stv.py --fast --float --noround csm8.blt > /dev/null; done
