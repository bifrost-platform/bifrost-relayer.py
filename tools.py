from tools.cmd_admin import admin_cmd
from tools.cmd_nominator import nominator_cmd
from tools import operator_cmd
from tools import user_cmd
from tools.utils import get_option_from_console

if __name__ == "__main__":

    tool_names = ["User", "Operator", "Nominator", "Admin"]
    while True:
        selected_tools = get_option_from_console("Select the tool you will use. ", tool_names)
        project_root_path = "./"

        if selected_tools == "User":
            user_cmd(project_root_path)

        elif selected_tools == "Nominator":
            nominator_cmd(project_root_path)

        elif selected_tools == "Operator":
            operator_cmd(project_root_path)

        if selected_tools == "Admin":
            admin_cmd(project_root_path)

        else:
            print("quited")
