import socket
import select
import errno
import boto3
from langdetect import detect
import sys
import threading

HEADER_LENGTH = 10
global target_lang
target_lang = 'en'
## getting the hostname by socket.gethostname() method
hostname = socket.gethostname()
## getting the IP address using socket.gethostbyname() method
ip_address = socket.gethostbyname(hostname)
## printing the hostname and ip_address
#print(f"Hostname: {hostname}")
#print(f"IP Address: {ip_address}")

IP = ip_address

PORT = 5000


# Create a socket
# socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
# socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to a given ip and port
client_socket.connect((IP, PORT))

# Set connection to non-blocking state, so .recv() call won;t block, just return some exception we'll handle
#client_socket.setblocking(False)



def sender():
    global target_lang
    my_username = input("Username: ")
    username = my_username.encode('utf-8')
    username_header = f"{len(username):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(username_header + username)
    while True:
        # If message is not empty - send it
        message = input(f'{my_username} > ')
        #print('message is in loop',' ',message)
        if message:
            ##detecting the langaugae of the sent message from client:
            client_lang = detect(message)
            #print('sent message and the language of the message from client is', ' ', message, ' ', client_lang)
            target_lang = client_lang

            # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
            message = message.encode('utf-8')
            message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
            client_socket.send(message_header + message)

        
def receiver():
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
        #print('received message language is', ' ', lang,' ','and target language is',' ',target_lang)

        translate = boto3.client(service_name='translate', region_name='us-west-2', use_ssl=True)
        translation = translate.translate_text(Text=message, SourceLanguageCode=lang,
                                               TargetLanguageCode=target_lang)
        translation_it = translation['TranslatedText']
        #print('translated text is', ' ', translation_it)


        # Print message
        print(f'{username} > {translation_it}')
    

sender_thread = threading.Thread(target=sender)
receiver_thread = threading.Thread(target=receiver)

sender_thread.start()
receiver_thread.start()

sender_thread.join()
receiver_thread.join()
