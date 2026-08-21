import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class RequestConsumer(AsyncJsonWebsocketConsumer):

    #########################################################
    # CONNECT
    #########################################################

    async def connect(self):

        print("✅ SOCKET CONNECTED")

        #################################################
        # TECHNICIAN GROUP
        #################################################

        self.group_name = 'technicians'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        #################################################
        # REQUEST-SPECIFIC TRACKING GROUP
        #################################################

        self.request_id = self.scope['url_route']['kwargs'].get('id')

        if self.request_id:

            self.tracking_group_name = f"tracking_{self.request_id}"

            await self.channel_layer.group_add(
                self.tracking_group_name,
                self.channel_name
            )

        #################################################
        # ACCEPT SOCKET
        #################################################

        await self.accept()

        #################################################
        # SEND CONNECT MESSAGE
        #################################################

        await self.send(text_data=json.dumps({
            'message': 'Connected'
        }))

    #########################################################
    # DISCONNECT
    #########################################################

    async def disconnect(self, close_code):

        print("❌ SOCKET DISCONNECTED")

        #################################################
        # REMOVE TECHNICIAN GROUP
        #################################################

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        #################################################
        # REMOVE TRACKING GROUP
        #################################################

        if hasattr(self, 'tracking_group_name'):

            await self.channel_layer.group_discard(
                self.tracking_group_name,
                self.channel_name
            )

    

    #########################################################
    # NEW REQUEST NOTIFICATION
    #########################################################

    async def new_request(self, event):

        print("🔥 CONSUMER RECEIVED EVENT")

        await self.send(text_data=json.dumps(
            event['content']
        ))

    #########################################################
    # REMOVE NOTIFICATION
    #########################################################

    async def notification_removed(self, event):

        print("🔥 notification_removed HIT")

        await self.send(text_data=json.dumps({
            'type': 'notification_removed',
            'request_id': event['request_id']
        }))

    #########################################################
    # TECHNICIAN MESSAGE
    #########################################################

    async def technicians_message(self, event):

        await self.send_json(event['content'])

    #########################################################
    # RECEIVE LIVE GPS
    #########################################################

    async def receive(self, text_data):

        data = json.loads(text_data)

        print("📩 RECEIVED:", data)

        #################################################
        # LIVE LOCATION TRACKING
        ##################################
        if data.get('type') == 'live_location':

            latitude = data.get('latitude')
            longitude = data.get('longitude')
            request_id = data.get('request_id')

            print(
                "📍 LIVE GPS:",
                latitude,
                longitude,
                "REQUEST:",
                request_id
            )

            #################################################
            # SEND TO REQUEST-SPECIFIC TRACKING GROUP
            #################################################

            if request_id:

                await self.channel_layer.group_send(

                    f"tracking_{request_id}",

                    {
                        'type': 'location_update',

                        'latitude': latitude,
                        'longitude': longitude,
                    }
                )

    #########################################################
    # SEND LIVE LOCATION TO CUSTOMER
    #########################################################

    async def location_update(self, event):

        await self.send(text_data=json.dumps({

            'type': 'location_update',

            'latitude': event['latitude'],
            'longitude': event['longitude'],

        }))