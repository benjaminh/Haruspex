def merge_dicts(dict_list):
    result = {}
    for dictionary in dict_list:
        result.update(dictionary)
    return result

def merge_egal_sple_dict(*dict_args, OCC):
    '''
    the dicts should be "key: occurrence_position, value: whatever"
    return a dict key: shortest shape in soft_equality; value dict{"equal_key":set of (occurrence_position), "equal_values": tuple of (whatever)}
    the new key gathering all the merged keys (found in sple_egal) will be the most occurring one.
    Given any number of dicts, shallow copy and merge into a new dict,
    based on egal_sple fonction.
    '''
    if len(dict_args) > 1:
        merged = merge_dicts(dict_args)
    else:
        merged = dict_args[0]

    if len(merged) == 1: # faster if there is only one pair of (key, value) in the dict!
        return merged
    else:
        ordered_keys = sorted(merged, key=lambda clef: len(merged[clef]), reverse=True)
        z = {}
        seen = {}
        for key1 in ordered_keys:
            equal_keys = set()
            equal_keys.add(key1)
            equal_values = (merged[key1],)#tuple init, not set because maybe duplicates
            for key2 in ordered_keys:
                if (OCC[key1].soft_eguality(OCC[key2]) and key2 not in equal_keys):
                    egual_keys.add(key2)
                    egual_values += (merged[key2])
            z[OCC[key1].ascii_shape] = {"equal_key":egual_keys, "equal_values":equal_values}
        return z


def count_nuc_cases(merged):
#{"equal_key":set of (occurrence_position), "equal_values": tuple of tuples(cand_id, link_word_type)}
# Four Cases!
    s1 = 0# s1: same linkword same CAND
    s2 = 0# s2: same linkword, different CAND
    s3 = 0# s3: different linkword, same CAND
    s4 = 0# s4: different linkword, different CAND
    for feature in merged["equal_values"]:#feature is tuple(cand_id, link_word_type)
        cand_id, link_word_type = feature
        #not able to count the seen ones because many times the same "feature" apears
        #TODO maybe a better solution than this one
        for feature2 in merged["equal_values"]:
            cand_id2, link_word_type2 = feature2
            if cand_id2 == cand_id and link_word_type2 == link_word_type:
                s1 += 1
            if cand_id2 != cand_id and link_word_type2 == link_word_type:
                s2 += 1
            if cand_id2 == cand_id and link_word_type2 != link_word_type:
                s3 += 1
            if cand_id2 != cand_id and link_word_type2 != link_word_type:
                s4 += 1
    s1 = math.sqrt(s1)
    s2 = math.sqrt(s2)
    s3 = math.sqrt(s3)
    s4 = math.sqrt(s4)
    return (s1, s2, s3, s4)


def soft_equality_set(occ_pos_set, OCC, threshold):
    #should be a set of occ_pos
    #returns a set of tuple containing equals pos if there is more than "threshold" equalities
    seen= set()
    equals = set()
    for pos in occ_pos_set:
        seen.add(pos)
        eq = (pos,)
        for pos2 in occ_pos_set:
            if OCC[pos].soft_equality(pos2) and pos2 not in seen:
                eq += (pos2,)
        if len(eq) >= threshold:
            equals.add(eq)
