from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import json


class ConnectDatabase():
    with open('config.json') as f:
        data = json.load(f)
        uri = data['MONGO']['URI']

    def insert_schedule_into_database(self, options, str_datetime, image_binary):
        # Create a new client and connect to the server
        client = MongoClient(self.uri, server_api=ServerApi('1'))
        database = client[f'{options}']

        """
        # Send a ping to confirm a successful connection
        try:
            database.create_collection()
        except Exception as e:
            print(f'{options} has already existed')
        """

        collection = database.get_collection(options)

        collection.insert_one({
            "_id": str_datetime,
            "image": image_binary
        })

        client.close()

    def select_schedule_from_database(self, options, str_datetime):

        # Create a new client and connect to the server
        client = MongoClient(self.uri, server_api=ServerApi('1'))
        database = client[f'{options}']

        collection = database.get_collection(options)

        result = collection.find_one({
            "_id": str_datetime
        })

        client.close()

        return result

    def update_schedule_set_database(self, options, str_datetime, image_binary):
        # Create a new client and connect to the server
        client = MongoClient(self.uri, server_api=ServerApi('1'))
        database = client[f'{options}']

        collection = database.get_collection(options)

        collection.update_one({
            "_id": str_datetime
        }, {
            "$set": {
                "image": image_binary
            }
        })

        client.close()
