#!/usr/env/bin python3

import Levenshtein

def match_something(item, list):
    item = item.replace(" ","")
    item = item.replace(".", "")
    item = item.replace(",", "")
    lowest = list[0]
    lowestdelta = Levenshtein.distance(item, list[0])
    for entry in list:
        delta = Levenshtein.distance(item, entry)
        if delta < lowestdelta:
            lowestdelta = delta
            lowest = entry

    print(delta, item, entry)
    return lowest


if __name__ == "__main__":
    result = match_something("t. v.", ['television', 'tcf', 'tv'])
    print(result)


