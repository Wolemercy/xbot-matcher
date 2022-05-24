import os
import datetime, collections, psycopg2, redis, requests
from dotenv import load_dotenv
from networkx import Graph
from networkx.algorithms.matching import max_weight_matching

load_dotenv()

def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode=os.getenv("SSL_MODE"))
        print("Connection to database successful")
        return conn
    except:
        print("An error occured while connecting to the Database")
        return False

def get_cache_connection():
    try:
        cache = redis.Redis(
            host=os.getenv("CACHE_HOST"),
            port=os.getenv("CACHE_PORT"),
            password=os.getenv("CACHE_PASSWORD"))
        
        cache.get('')
        print("Connection to cache successful")
        return cache
    except:
        print("An error occured while connecting to the Cache")
        return False
    

def get_candidates(cache, guild_id):
    cache_key = 'SUMPOOL-' + guild_id
    candidates = cache.smembers(cache_key)
    if not candidates:
        print("There are no candidates available for matching")
        return {}
    else:
        print("Successfully returned list of candidates from cache")
        new_candidates = set()
        for candidate in candidates:
            decoded_candidate = candidate.decode('utf-8')
            if decoded_candidate != "":
                new_candidates.add(decoded_candidate)
        return new_candidates

def retrieve_previous_matches(cursor, guild_id):
    select_statement = """SELECT "dUserId", "dUserMatchedId", "createdAt" 
                            FROM "ServerUserMatch"
                            WHERE "dGuildId" = %s
                        """
    data = guild_id
    cursor.execute(select_statement, (data,))

    previous_matches = collections.defaultdict(set)

    for record in cursor.fetchall():
        previous_matches[record[0]].add(record[1])
    
    print("Successfully returned previous matches: ", previous_matches)
    return previous_matches


def make_matches(candidates, previous_matches):
    if len(candidates) <= 1:
        print("A match could not be made because there aren't enough candidates")
        return None, None
    G = Graph()
    G.add_nodes_from(candidates)

    for u in candidates:
        G.add_edges_from((u, v) for v in candidates.difference(previous_matches[u]).difference({u}))
    matches = max_weight_matching(G)

    print("candidates", candidates)
    print(matches)
    matched_candidates = set()
    for first, second in matches:
        matched_candidates.add(first)
        matched_candidates.add(second)

    unmatched_candidates = candidates.difference(matched_candidates)
    
    unmatched_candidates = list(unmatched_candidates)

    left, right = 0, len(unmatched_candidates) - 1

    while left < right:
        matches.add((unmatched_candidates[left], unmatched_candidates[right]))
        matched_candidates.update({unmatched_candidates[left], unmatched_candidates[right]})
        left += 1
        right -= 1

    # if unmatched_candidates are odd, then there's one remaining unmatched candidate and left index equals right index
    unmatched_element = None
    if left == right:
        unmatched_element = unmatched_candidates[left]

    print("Successfully matched available candidates")
    return matches, unmatched_element

def falsify_previous_matches(conn, cursor, guild_id):
    update_statement = """UPDATE "ServerUserMatch"
                            SET "isMatchActive" = %s
                            WHERE "dGuildId" = %s AND "isMatchActive" = %s
                        """
    data = (False, guild_id, True)
    cursor.execute(update_statement, data)
    conn.commit()
    print("All previous matches have been made inactive")
    return

def record_matches(conn, cursor, guild_id, matches, unmatched_candidate):

    if not matches:
        print("There are no new matches to be recorded")
        return

    # TODO: Refactor insert to execute_values
    insert_statement = """INSERT INTO "ServerUserMatch" ("dGuildId", "dUserId", "dUserMatchedId", "isMatchActive", "createdAt", "updatedAt")
                            VALUES(%s, %s, %s, %s, %s, %s)
                        """
    for match in matches:
        first, second = match
        insert_time = update_time = datetime.datetime.now(), 
        data_first_second = (guild_id, first, second, True, insert_time, update_time)
        cursor.execute(insert_statement, data_first_second)
        data_second_first = (guild_id, second, first, True, insert_time, update_time)
        cursor.execute(insert_statement, data_second_first)
        print("A new match has been added to the database")

    if unmatched_candidate:
        # pair the unmatched candidate with the last set of matched candidates
        first, second, third = first, second, unmatched_candidate
        insert_time = update_time = datetime.datetime.now()

        # first and unmatched candidate
        data_first_third = (guild_id, first, third, True, insert_time, update_time)
        cursor.execute(insert_statement, data_first_third)

        data_third_first = (guild_id, third, first, True, insert_time, update_time)
        cursor.execute(insert_statement, data_third_first)

        # second and unmatched candidate
        data_second_third = (guild_id, second, third, True, insert_time, update_time)
        cursor.execute(insert_statement, data_second_third)

        data_third_second = (guild_id, third, second, True, insert_time, update_time)
        cursor.execute(insert_statement, data_third_second)
        print("Two new matches have been added to the database")

    conn.commit()
    print("All matches have been saved to the database")
    return
        
def update_next_match_date(conn, cursor, guild_id):

    # first, get next_match date
    select_statement = """SELECT "matchFrequency"
                            FROM "Match"
                            WHERE "dGuildId" = %s
                        """
    select_data = guild_id
    cursor.execute(select_statement, (select_data,))

    result = cursor.fetchone()
    if not result:
        print("There is no match record for Guild {}".format(guild_id))
        return 

    match_frequency = result[0]
    match_frequency = datetime.timedelta(match_frequency)
    last_match_date = datetime.datetime.now()
    next_match_date = last_match_date + match_frequency

    # update last match date and next match date
    update_statement = """UPDATE "Match"
                            SET "lastMatchDate" = %s, "nextMatchDate" = %s
                            WHERE "dGuildId" = %s
                        """
    update_data = (last_match_date, next_match_date, guild_id)
    cursor.execute(update_statement, update_data)
    print("The next match date has been updated")
    conn.commit()
    print("The next match date has been saved to the database")
    return

def delete_pool_from_cache(cache, guild_id):
    cache_key = 'SUMPOOL-' + guild_id
    cache.delete(cache_key)
    print("Candidate pool removed from cache successfully")
    return

def send_response(guild_id):
    data = {
        "id": guild_id
    }
    url = os.getenv("MATCH_URL")

    try:
        r = requests.post(url, data, timeout=os.getenv("REQUEST_TIMEOUT"))
        print("Server has been notified of a successful set of matches", r.status_code)
    except:
        print("An error occured while notifying server of a successful set of matches")
    return


def matcher(guild_id):
    print("Getting DB Connection")
    conn = get_db_connection()
    
    print("Getting Cache Connection")
    cache = get_cache_connection()

    if not conn or not cache:
        return
    
    cursor = conn.cursor()
    previous_matches = retrieve_previous_matches(cursor, guild_id)

    # # candidates should be a set; cache_key = SUMPOOL-${guild_id}
    candidates = get_candidates(cache, guild_id)

    # make new matches
    new_matches, unmatched_candidate = make_matches(candidates, previous_matches)

    # falsify previous matches
    falsify_previous_matches(conn, cursor, guild_id)

    # record new matches
    record_matches(conn, cursor, guild_id, new_matches, unmatched_candidate)

    # update next match date
    update_next_match_date(conn, cursor, guild_id)

    # delete candidates pool from cache
    delete_pool_from_cache(cache, guild_id)

    # send response to webhook
    send_response(guild_id)

    cursor.close()
    cache.close()
    return


def call_matcher(guild_id):
    matcher(guild_id)