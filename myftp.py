#import socket module
from socket import *
import sys # In order to terminate the program

def quitFTP(clientSocket):
    command = "QUIT" + "\r\n"  # added QUIT cmd followed by new line
    dataOut = command.encode("utf-8")
    clientSocket.sendall(dataOut)
    dataIn = clientSocket.recv(1024)
    data = dataIn.decode("utf-8")
    print(data)

def sendCommand(socket, command):
    dataOut = command.encode("utf-8")
    socket.sendall(dataOut)  # send the command over the control connection
    dataIn = socket.recv(1024)  # read the server reply from the control connection
    data = dataIn.decode("utf-8")  # convert bytes to a string so we can check status codes
    return data

def receiveData(clientSocket):
    dataIn = clientSocket.recv(1024)
    data = dataIn.decode("utf-8")
    return data

# If you use passive mode you may want to use this method but you have to complete it
# You will not be penalized if you don't
def modePASV(clientSocket):
    command = "PASV" + "\r\n"
    data = sendCommand(clientSocket, command)  # send PASV and receive the 227 reply text
    status = 0
    if data.startswith("227"):
        status = 227

        start = data.find("(")  # find the start of the data connection (IP and port)
        end = data.find(")")  # find the end of the data connection (IP and port)
        numbers = data[start+1:end].split(",")  # split into the 6 comma-separated values

        ip = ".".join(numbers[0:4])  # convert address numbers into a dotted Internet Protocol string
        port = int(numbers[4]) * 256 + int(numbers[5])  # compute the port from p1*256 + p2

        dataSocket = socket(AF_INET, SOCK_STREAM)  # create the data connection socket (new per transfer)
        dataSocket.connect((ip, port))
        return status, dataSocket

    return status, None  # if PASV failed, return None for the data socket

def main():
    if len(sys.argv) != 2:  # enforce required command line format: python myftp.py server-name
        print("Usage: python myftp.py server-name")  # tell user correct way to run
        sys.exit()  # stop if no server name is provided

    username = input("Enter the username: ")
    password = input("Enter the password: ")
    clientSocket = socket(AF_INET, SOCK_STREAM) # TCP socket

    HOST = sys.argv[1]  # server name or Internet Protocol address comes from command line
    clientSocket.connect((HOST, 21))  # connect control connection to server port 21

    dataIn = receiveData(clientSocket)
    print(dataIn)

    status = 0
    if dataIn.startswith("220"):
        status = 220

    if status != 220:  # stop early if server did not greet properly
        print("Failure: did not receive 220 greeting.")  # error message
        clientSocket.close()  # close control connection
        sys.exit()  # terminate program

    print("Sending username")
    command = "USER " + username + "\r\n"  # build USER command with username
    dataIn = sendCommand(clientSocket, command)  # send USER and get response
    print(dataIn)

    if dataIn.startswith("331"):
        status = 331

    if status != 331:  # if server did not request password, login flow failed
        print("Failure: did not receive 331 after USER.")  # error message
        clientSocket.close()  # close control socket
        sys.exit()  # terminate program

    print("Sending password")
    command = "PASS " + password + "\r\n"  # build PASS command with password
    dataIn = sendCommand(clientSocket, command)  # send PASS and get response
    print(dataIn)

    if dataIn.startswith("230"):
        status = 230

    if status != 230:  # stop if login failed, possibly with 530 error code
        print("Failure: login unsuccessful.")  # error message
        clientSocket.close()  # close control socket
        sys.exit()  # terminate program


    # After successful login, we build the ls and quit commands
    while True:  # loop to test ls multiple times without reconnecting
        userCmd = input("myftp> ").strip()  # show the client prompt and read a command

        if userCmd == "ls":  # map ls to the FTP LIST command
            pasvStatus, dataSocket = modePASV(clientSocket)  # enter passive mode and open data connection
            if pasvStatus == 227 and dataSocket is not None:  # only proceed if passive mode succeeded
                listResp = sendCommand(clientSocket, "LIST\r\n")  # ask server to send directory listing
                print(listResp)  # show 150/125 type message from the server

                totalBytes = 0  # track bytes transferred for the required success message
                listingBytes = b""  # store bytes received from the data connection

                while True:  # read until server closes the data connection (end of listing)
                    chunk = dataSocket.recv(4096)  # receive part of the listing
                    if not chunk:  # no more data means the server closed data connection
                        break  # exit the loop
                    listingBytes += chunk  # append this chunk to full listing
                    totalBytes += len(chunk)  # add to byte count

                dataSocket.close()  # close the data connection after one transfer 
                print(listingBytes.decode("utf-8", errors="replace"), end="")  # print directory listing text

                finalResp = receiveData(clientSocket)  # read final control reply, possible code 226 transfer complete
                print(finalResp)  # display completion message
                print(f"Success. {totalBytes} bytes transferred.")  # required success output with byte count
            else:
                print("Failure: passive mode (PASV) did not return 227.")  # explain why ls failed

        elif userCmd.startswith("get "):  # map get to the FTP RETR command
            parts = userCmd.split(" ", 1)  # split into command and filename
            filename = parts[1].strip()  # extract the remote filename

            pasvStatus, dataSocket = modePASV(clientSocket)  # enter passive mode and open data connection
            if pasvStatus == 227 and dataSocket is not None:  # only proceed if passive mode succeeded
                retrResp = sendCommand(clientSocket, "RETR " + filename + "\r\n")  # ask server to send the file
                print(retrResp)  # show 150 type message from the server

                if retrResp.startswith("150"):  # server is ready to send the file
                    totalBytes = 0  # track bytes transferred for the required success message
                    fileBytes = b""  # store bytes received from the data connection

                    while True:  # read until server closes the data connection (end of file)
                        chunk = dataSocket.recv(4096)  # receive part of the file
                        if not chunk:  # no more data means the server closed data connection
                            break  # exit the loop
                        fileBytes += chunk  # append this chunk to full file data
                        totalBytes += len(chunk)  # add to byte count

                    dataSocket.close()  # close the data connection after one transfer

                    with open(filename, "wb") as f:  # open local file in binary write mode
                        f.write(fileBytes)  # write downloaded bytes to local file

                    finalResp = receiveData(clientSocket)  # read final control reply, expecting 226 transfer complete
                    print(finalResp)  # display completion message
                    print(f"Success. {totalBytes} bytes transferred.")  # required success output with byte count
                else:
                    dataSocket.close()  # close data socket on failure
                    print("Failure: server could not send file.")  # error message for RETR failure
            else:
                print("Failure: passive mode (PASV) did not return 227.")  # explain why get failed

        elif userCmd.startswith("put "):  # map put to the FTP STOR command
            parts = userCmd.split(" ", 1)  # split into command and filename
            filename = parts[1].strip()  # extract the local filename

            try:
                with open(filename, "rb") as f:  # open local file in binary read mode
                    fileData = f.read()  # read entire file into memory
            except FileNotFoundError:
                print("Failure: local file not found.")  # error if file does not exist locally
                continue  # go back to prompt

            pasvStatus, dataSocket = modePASV(clientSocket)  # enter passive mode and open data connection
            if pasvStatus == 227 and dataSocket is not None:  # only proceed if passive mode succeeded
                storResp = sendCommand(clientSocket, "STOR " + filename + "\r\n")  # tell server to receive file
                print(storResp)  # show 150 type message from the server

                if storResp.startswith("150"):  # server is ready to receive the file
                    dataSocket.sendall(fileData)  # send all file bytes over the data connection
                    dataSocket.close()  # close data connection to signal end of file transfer

                    finalResp = receiveData(clientSocket)  # read final control reply, expecting 226 transfer complete
                    print(finalResp)  # display completion message
                    print(f"Success. {len(fileData)} bytes transferred.")  # required success output with byte count
                else:
                    dataSocket.close()  # close data socket on failure
                    print("Failure: server could not accept file.")  # error message for STOR failure
            else:
                print("Failure: passive mode (PASV) did not return 227.")  # explain why put failed
                
        elif userCmd.startswith("cd "):  # change remote directory
            directory = userCmd.split(" ", 1)[1].strip()
            resp = sendCommand(clientSocket, "CWD " + directory + "\r\n")
            print(resp)

        elif userCmd.startswith("delete "):  # delete remote file
            filename = userCmd.split(" ", 1)[1].strip()
            resp = sendCommand(clientSocket, "DELE " + filename + "\r\n")
            print(resp)

        elif userCmd == "quit":  # quit command to end session
            quitFTP(clientSocket)  # send QUIT to server
            print("Disconnecting...")  # disconnecting message
            clientSocket.close()  # close control socket
            sys.exit()  # terminate program after quit

        else:
            print("Supported commands for this stage: ls, quit")  # supported commands

main()
