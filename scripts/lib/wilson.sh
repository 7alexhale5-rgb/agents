#!/usr/bin/env bash
# wilson.sh — Wilson lower-CI (95%) for binomial p̂ given successes k and trials n.
# Sourced by eval runners and the registry-rebuild stats summary.
#
# Usage (sourced):
#   source scripts/lib/wilson.sh
#   wilson_lower 127 150   # → 0.7956
#
# Usage (direct):
#   bash scripts/lib/wilson.sh 127 150

wilson_lower () {
  awk -v k="$1" -v n="$2" 'BEGIN {
    if (n == 0) { print "0.0000"; exit }
    z = 1.96; p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    margin = (z * sqrt((p*(1-p) + z*z/(4*n))/n)) / denom
    lo = centre - margin
    if (lo < 0) lo = 0
    printf "%.4f", lo
  }'
}

# When invoked directly (not sourced), pass through to the function.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  if [ "$#" -ne 2 ]; then
    echo "usage: $0 <successes> <trials>" >&2
    exit 1
  fi
  wilson_lower "$1" "$2"
  echo
fi
