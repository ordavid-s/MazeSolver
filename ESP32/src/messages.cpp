
#include "messages.h"

/**
 * Creates an acknowledge message and send it back to the RPI.
 */
void buildAndSendAckMsg(WiFiClient *client, MSG direction_msg)
{
    MSG ack;
    ack.opcode = OPCODES::ESP32_ACK;
    ack.src_device = DEVICE::ESP_32;
    ack.dst_device = DEVICE::RSP;
    ack.direction = direction_msg.direction;
    ack.time_angle = direction_msg.time_angle;
    ack.speed_right_wheel = direction_msg.speed_right_wheel;
    ack.speed_left_wheel = direction_msg.speed_left_wheel;

    client->write((uint8_t *)&ack, sizeof(ack));
}

/**
 * Creates a request message and send it to the RPI.
 */
void requestDirection(WiFiClient *client)
{
    MSG requestMsg;
    requestMsg.opcode = (unsigned char)(OPCODES::DIRECTION_REQUEST);
    requestMsg.src_device = (unsigned char)DEVICE::ESP_32;
    requestMsg.dst_device = (unsigned char)DEVICE::RSP;
    requestMsg.direction = (unsigned char)0;
    requestMsg.time_angle = (int)0;
    requestMsg.speed_right_wheel = (int)0;
    requestMsg.speed_left_wheel = (int)0;

    client->write((uint8_t *)&requestMsg, sizeof(requestMsg));
}

/**
 * Read the incoming message to the buffer. (from RPI)
 */
int readMessage(MSG *directionMsg, WiFiClient *client)
{
    int bytesRemain = sizeof(*directionMsg);
    int directionMsgCounter = 0;

    while (bytesRemain > 0)
    {
        bytesRemain -= client->read((uint8_t *)directionMsg, bytesRemain);
        if (bytesRemain > 0 && directionMsgCounter > MAX_TEMPS_BEFORE_BREAK)
        {
            return ERROR;
        }
        if (bytesRemain > 0)
        {
            directionMsgCounter++;
            delay(500);
        }
    }
    return SUCCESS;
}

/**
 * Checks if the client is available.
 * There is a timeout of 2 seconds if there isnt a response from client.
 */
int waitForClient(WiFiClient *client)
{
    int check_connection_counter = 0;
    while (client->available() <= 0)
    {
        delay(200);
        check_connection_counter++;
        if (check_connection_counter > MAX_TEMPS_BEFORE_BREAK)
        {
            return ERROR;
        }
    }

    return SUCCESS;
}
