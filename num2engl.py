units = ["", "one", "two", "three", "four",  "five", 
    "six", "seven", "eight", "nine "]

teens = ["", "eleven", "twelve", "thirteen",  "fourteen", 
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]

tens = ["", "ten", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety"]

thousands = ["","thousand", "million",  "billion",  "trillion", 
    "quadrillion",  "quintillion",  "sextillion",  "septillion", "octillion", 
    "nonillion",  "decillion",  "undecillion",  "duodecillion",  "tredecillion", 
    "quattuordecillion",  "sexdecillion",  "septendecillion",  "octodecillion", 
    "novemdecillion",  "vigintillion "]


def num2words(num):
    words = []
    if num == 0:
        words.append("zero")
    else:
        numStr = "%d" % num
        numStrLen = len(numStr)
        groups = (numStrLen + 2) / 3
        groups = int(groups)
        numStr = numStr.zfill(groups * 3)
        for i in range(0, groups*3, 3):
            h = int(numStr[i])
            t = int(numStr[i+1])
            u = int(numStr[i+2])
            g = groups - (i / 3 + 1)
            
            if h >= 1:
                words.append(units[h])
                words.append("hundred")
                
            if t > 1:
                words.append(tens[t])
                if u >= 1:
                    words.append(units[u])
            elif t == 1:
                if u >= 1:
                    words.append(teens[u])
                else:
                    words.append(tens[t])
            else:
                if u >= 1:
                    words.append(units[u])
            
            if g >= 1 and (h + t + u) > 0:
                words.append(thousands[g])

    return words