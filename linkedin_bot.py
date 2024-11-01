# This is a bot I am building using langchain to automatically select jobs on LinkedIn

import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from bs4 import BeautifulSoup

# 1. Set up Selenium WebDriver
driver_path = './chromedriver.exe'


USER="Alberto Eusebio"

CHATS_PATH = './chats/'

load_dotenv()

@tool
def get_chat(name: str, surname: str) -> str:
    """
        Given the name and surname of a contact, return the corresponding chat transcript.
    """
    chat_name = name + '_' + surname + '.txt'
    chat_path = os.path.join(CHATS_PATH, chat_name)
    with open(chat_path, 'r') as f:
        return f.read()
    return "chat not found"

@tool
def gent_chat_names() -> str:
    """
        Return the list of chat names in the chat directory
    """
    return os.listdir(CHATS_PATH)

@tool
def write_to_chat(name: str, surname: str, message: str) -> str:
    """
        Write the message to the chat with the given name and surname
    """
    chat_name = name + '_' + surname + '.txt'
    chat_path = os.path.join(CHATS_PATH, chat_name)
    with open(chat_path, 'a') as f:
        f.write(message)
    return "Message written to chat"

@tool
def get_latest_chats():
    """
        Get the names of the people in the user feed on LinkedIn
        and return the last message of each chat
    """
    driver = webdriver.Chrome()
    driver.get("https://www.linkedin.com/messaging/")
    time.sleep(5)
    
    USERNAME = os.getenv("LINKEDIN_USERNAME")
    PASSWORD = os.getenv("LINKEDIN_PASSWORD")

    # login
    username_input = driver.find_element(By.ID, "username")
    username_input.send_keys(USERNAME)
    password_input = driver.find_element(By.ID, "password")
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)
    
    time.sleep(20)

    # 4. Extract page content using Beautiful Soup
    soup = BeautifulSoup(driver.page_source, "html.parser")

    #print(soup.prettify())

    chat_names = list()

    # get chats
    print("Getting chats")
    chats = soup.find_all("div", {"class": "msg-conversation-card msg-conversations-container__pillar"})
    for chat in chats:
        user_name = chat.find("span", {"class": "truncate"}).get_text(strip=True)
        chat_script = chat.find("p").get_text(strip=True)
        chat_names.append(user_name + ": " + chat_script)
    time.sleep(20)
    driver.quit()

    return chat_names



def main():

    def should_continue(state: MessagesState):
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return END

    def call_model(state: MessagesState):
        messages = state["messages"]
        response = model.invoke(messages)
        return {"messages": [response]}


    # Define the tools that the model can use
    tools = [get_chat, gent_chat_names, write_to_chat, get_latest_chats]

    # define the model nodes
    tool_node = ToolNode(tools)

    # Define the model to be used
    model = ChatOpenAI(model="gpt-4o", temperature=0.5).bind_tools(tools)

    # Define the state graph
    workflow = StateGraph(MessagesState)

    # Define the two nodes we will cycle between
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    # Compile the workflow
    app = workflow.compile()

    for chunk in app.stream({"messages": [("human", f"{USER}: I need you to summarize my chats")]}, stream_mode="values",):
        chunk["messages"][-1].pretty_print()


if __name__ == '__main__':
    main()