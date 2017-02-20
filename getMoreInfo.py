import nltk
import nltk.data
import wikipedia
import sys
import fileinput
index_disambig = -1;
def main():
    #print('done')
    print("Enter Input:")
    for line in fileinput.input():
        try:
            getMoreInfo(line, 2)
        except wikipedia.exceptions.PageError as e:
            print("Invalid topic, try again!")

def getMoreInfo(str, num_sentences):
    nltk.download("punkt")
    global index_disambig
    index_disambig +=1
    try:
        summary = (wikipedia.summary(str, sentences = num_sentences+1))
    except wikipedia.exceptions.DisambiguationError as e:
        #global index_disambig = global index_disambig +1
        return getMoreInfo(e.options[index_disambig], num_sentences)




    tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
    sentence_list = tokenizer.tokenize(summary)
    out_str = ""
    counter = 0;
    for sentence in sentence_list:
        if counter == 0:
            #dont print
            counter +=1
        else:
            out_str = out_str + " "+ sentence
    #print(sentence_list[1]);
    #print(sentence_list[2]);
    print(out_str)
    sys.stdout.flush()
    return(out_str);


if __name__ == "__main__":
    main()
