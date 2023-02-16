from tools.cmd_admin import admin_cmd
from tools.cmd_operator import operator_cmd
from tools.cmd_user import user_cmd
from tools.utils import get_option_from_console

PROJECT_ROOT_PATH = "./"

if __name__ == "__main__":
    user_roles = ["User", "Operator", "Admin"]

    while True:
        # select network type
        network_type = get_option_from_console("Select Network Type ", ["testnet", "mainnet"])
        is_testnet = True if network_type == "testnet" else False

        # get user's role
        selected_tools = get_option_from_console("What is your role? ", user_roles)

        if selected_tools == "User":
            user_cmd(is_testnet)

        elif selected_tools == "Operator":
            operator_cmd(is_testnet)

        if selected_tools == "Admin":
            admin_cmd(is_testnet)

        else:
            print("quited")
