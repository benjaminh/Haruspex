
def idf():
    idf = {}
    nb_pages = len(dict_bypage) #how many pages there are
    for keyword in dict_bykey:
        idf = math.log10(nb_pages/len(set(dict_bykey[keyword])))
        idf[keyword] = idf
    return idf

def build_links_TFiDF():
    idf = idf()
    done = set()
    with open('links.csv') as linksfile:
        for key in dict_bykey: #each key in a page will be a link
            nb_occurrences_of_key_inpage = Counter(dict_bykey[key]) #return smth like {'pagenumber1': 2 ; 'pagenumber5': 3 ; 'pagenumberx': y}
            for page_number in nb_occurrences_of_key_inpage:
                for p_num in nb_occurrences_of_key_inpage:
                    linked = str(page_number + '@' + p_num)
                    deknil = str(p_num + '@' + page_number)
                    if (page_number != p_num and deknil not in done):
                        tf = nb_occurrences_of_key_inpage[p_num] + nb_occurrences_of_key_inpage[page_number]
                        tfidf = tf*idf[key]
                        done.append(linked)
                        link = linked + key + str(tfidf)
                        linksfile.write(link)
