"""
    A few functions that need to be called many times, often in different files.
"""
# setup logging
from logging_th import logger
global log
log = logger()


def db_format_channel(channel_info: list):
    """
        Format the list of tuples that the channels db returns into a dict

        return:
            {
                channelID: "channelID",
                channel_name: "channel_name",
                public: False
            }
    """



    # this type of operation can crash the server if I fuck something up in the table
    # I need an error message bc this seems like it would be really hard to debug otherwise
    try:
        channel_obj = {
                "channelID": channel_info[0],
                "channel_name": channel_info[1],
                "public": channel_info[2]
                }
    except Exception as e:
        log.error(db_format_channel, f"Corrupted information in channels table. {e = }")
        return "Internal database error while fetching channel information", 500


    return channel_obj, 200


def db_format_message(messages: list):
    """ Formats the output of the db response of the messages table """


    try:
        messages_list = []
        for message in messages:

            message_obj = {
                    "messageID": message[0],
                    "channelID": message[1],
                    "userID"   : message[2],
                    "replyID"  : message[3],
                    "keyID"    : message[4],
                    "send_time": message[5],
                    "type"     : message[6],
                    "data"     : message[7],
                    }

            messages_list.append(message_obj)

    except Exception as e:
        log.error(db_format_message, f"An error occured while formatting message: {e}.")
        return f"Internal database error wile formatting messages.", 500

    return messages_list, 200