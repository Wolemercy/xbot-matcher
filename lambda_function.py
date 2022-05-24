import json
from xbot_matcher import call_matcher

def lambda_handler(event, context):
    guild_id = event["guildId"]
    
    print("Calling Matcher for Server with GuildId: {}".format(guild_id))
    
    call_matcher(guild_id)
    
    print("Finished calling Matcher for Server with GuildId: {}".format(guild_id))

    return {
        'statusCode': 200,
        'body': json.dumps("Matcher Ran Successfully")
    }
