import socket
import select
import errno
import boto3
from langdetect import detect
import sys

HEADER_LENGTH = 10

target = 'en'
## getting the hostname by socket.gethostname() method
hostname = socket.gethostname()
## getting the IP address using socket.gethostbyname() method
ip_address = socket.gethostbyname(hostname)
## printing the hostname and ip_address
print(f"Hostname: {hostname}")
print(f"IP Address: {ip_address}")

IP = ip_address

PORT = 5000
my_username = input("Username: ")

# Create a socket
# socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
# socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to a given ip and port
client_socket.connect((IP, PORT))

# Set connection to non-blocking state, so .recv() call won;t block, just return some exception we'll handle
client_socket.setblocking(False)

# Prepare username and header and send them
# We need to encode username to bytes, then count number of bytes and prepare header of fixed size, that we encode to bytes as well
username = my_username.encode('utf-8')
username_header = f"{len(username):<{HEADER_LENGTH}}".encode('utf-8')
client_socket.send(username_header + username)

while True:

    # Wait for user to input a message
    message = input(f'{my_username} > ')

    # If message is not empty - send it
    if message:

        ##detecting the langaugae of the sent message from client:
        client_lang = detect(message)
        print('sent message and the language of the message from client is', ' ', message, ' ', client_lang)

        target = client_lang
        # if not user_lang:
        #     user_lang[user["data"].decode("utf-8")] = lang
        #     print(user_lang)
        # else:
        #     if user["data"].decode("utf-8") not in user_lang:
        #         user_lang[user["data"].decode("utf-8")] = lang
        #         print(user_lang)

        # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
        message = message.encode('utf-8')
        message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
        client_socket.send(message_header + message)



    try:
        # Now we want to loop over received messages (there might be more than one) and print them
        while True:

            # Receive our "header" containing username length, it's size is defined and constant
            username_header = client_socket.recv(HEADER_LENGTH)

            # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
            if not len(username_header):
                print('Connection closed by the server')
                sys.exit()

            # Convert header to int value
            username_length = int(username_header.decode('utf-8').strip())

            # Receive and decode username
            username = client_socket.recv(username_length).decode('utf-8')

            # Now do the same for message (as we received username, we received whole message, there's no need to check if it has any length)
            message_header = client_socket.recv(HEADER_LENGTH)
            message_length = int(message_header.decode('utf-8').strip())
            message = client_socket.recv(message_length).decode('utf-8')

            ### translating message before printing######

            ##detecting the langaugae of the received message:
            lang = detect(message)
            print('received message language is', ' ', lang,' ','and target language is',' ',target)

            translate = boto3.client(service_name='translate', region_name='us-west-2', use_ssl=True)
            translation = translate.translate_text(Text=message, SourceLanguageCode=lang,
                                                   TargetLanguageCode=target)
            translation_it = translation['TranslatedText']
            print('translated text is', ' ', translation_it)

            # if username not in user_lang:
            #     translate = boto3.client(service_name='translate', region_name='us-west-2', use_ssl=True)
            #     translation = translate.translate_text(Text=message, SourceLanguageCode=lang, TargetLanguageCode='en')
            #     translation_it = 'Please respond in your language to get chat in your language.' + ' ' + translation[
            #         'TranslatedText']
            #     print('first translation is', ' ', translation_it)
            # else:
            #     translate = boto3.client(service_name='translate', region_name='us-west-2', use_ssl=True)
            #     translation = translate.translate_text(Text=message, SourceLanguageCode=lang, TargetLanguageCode=user_lang[username])
            #     translation_it = translation['TranslatedText']
            #     print('translated text is', ' ', translation_it)
         ####################################################################

            # Print message
            print(f'{username} > {translation_it}')

    except IOError as e:
        # This is normal on non blocking connections - when there are no incoming data error is going to be raised
        # Some operating systems will indicate that using AGAIN, and some using WOULDBLOCK error code
        # We are going to check for both - if one of them - that's expected, means no incoming data, continue as normal
        # If we got different error code - something happened
        if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
            print('Reading error: {}'.format(str(e)))
            sys.exit()

        # We just did not receive anything
        continue

    except Exception as e:
        # Any other exception - something happened, exit
        print('Reading error: '.format(str(e)))
        sys.exit()