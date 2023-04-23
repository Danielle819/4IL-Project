
# login for cmd, not for gui
def login(username, password):
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["login_msg"], username + "#" + password)
    if response == commprot.SERVER_CMD["error_msg"]:
        print(commprot.DATA_MESSAGES[_])
        return
    elif response == commprot.SERVER_CMD["success_msg"]:
        print("You logged in successfully!")
    else:
        print("login func:", response, _)
        return

    global listen_socket
    global server_socket
    global listen
    # setting up listening socket
    hostname = socket.gethostname()
    ipadd = socket.gethostbyname(hostname)
    port = random.randint(49152, 65535)
    listen_socket = socket.socket()
    listen_socket.bind((ipadd, int(port)))
    listen_socket.listen(1)

    response, _ = "", ""
    # server_socket = None
    build_and_send_message(commprot.CLIENT_CMD["my_address_msg"], ipadd + "#" + str(port))
    server_socket, add = listen_socket.accept()
    response, _ = recv_message_and_parse()
    if response == commprot.SERVER_CMD["error_msg"]:
        print(commprot.DATA_MESSAGES[_])
        return
    elif response == commprot.SERVER_CMD["success_msg"]:
        print("server connected successfully")
        listen = True
        # listen_th = threading.Thread(target=receive_invitation)
        # listen_th.start()


def receive_invitation():
    print("entered receive_invitation func")
    global listen
    global listen_socket
    global server_socket
    global invitations
    global edit_invitations_list

    while listen:
        # print_input_lock.acquire()
        # print("receive_invitation func waiting for an invitation...")
        # print_input_lock.release()
        try:
            cmd, data = recv_message_and_parse(sock=server_socket)
            # print_input_lock.acquire()
            # print("receive_invitation func an invitation was received!")
            # print("cmd:", cmd, "data:", data)
            # print_input_lock.release()
            if cmd == commprot.SERVER_CMD["playing_invitation_msg"]:
                build_and_send_message(commprot.CLIENT_CMD["invitation_received_msg"], "", sock=server_socket)
                edit_invitations_list.acquire()
                invitations.append(data)
                edit_invitations_list.release()
                print("\n", data, "has invited you to a game!")
            elif cmd == commprot.SERVER_CMD["remove_invitation_msg"]:
                edit_invitations_list.acquire()
                try:
                    invitations.remove(data)
                except ValueError:
                    print("receive_invitation func - removed invitation was not in invitations")
                else:
                    print("\n", data, "has removed their playing invitation to you")
                edit_invitations_list.release()
            else:
                build_and_send_message("", "", sock=server_socket)

        except OSError and Exception as e:
            print("receive_invitation func error:", e)
            break

    print("receive_invitation DONE")
    listen = False


# GAME outdated functions
def get_place(board, col):
    if col == "E":
        return "E"

    while not check_col(board, col):
        print("inaccessible place, try again.")
        col = get_col()

    row = board.shape[0] - 1
    while board[row, col] != 0:
        row -= 1

    return row, col


def get_col():
    col = None
    while col is None:
        col = input("choose col (or e to exit): ")
        if col == "e" or col == "E":
            return "E"
        else:
            try:
                col = int(col)
            except ValueError:
                print("invalid input. try again")
                col = None
    return col


def check_col(board, col):
    if col >= board.shape[1] or col < 0:
        return False

    return board[0, col] == 0
