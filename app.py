import time
import json
import yfinance as yf
import openai
import streamlit as st
from lightweight_charts.widgets import StreamlitChart


import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


# =====< Python function >======================================================

def get_stock_price(ticker):
    data = yf.Ticker(ticker).history(period="1mo").iloc[-1].Close
    return str(data)




# =====< OpenAI function call >=================================================

def run_conversation(prompt):
    messages = [{"role": "user", "content": prompt}]
    functions = [
        {
            "name": "get_stock_price",
            "description": "Give the latest closed price of a ticker symbol of a company",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "The ticker symbol for the stock of a company (e.g. MSTF for Microsoft)",
                    },
                },
                "required": ["ticker"],
            },
        }
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
        functions=functions,
        function_call="auto",  # auto is default, but we'll be explicit
    )
    response_message = response["choices"][0]["message"]
    print("\n---------< first response >----------")
    print(response_message)


    if response_message.get("function_call"):
        available_functions = {
            "get_stock_price": get_stock_price,
        }  # only one function in this example, but you can have multiple
        function_name = response_message["function_call"]["name"]
        fuction_to_call = available_functions[function_name]
        function_args = json.loads(response_message["function_call"]["arguments"])
        info_ticker = function_args.get("ticker")
        function_response = fuction_to_call(
            ticker=function_args.get("ticker"),
        )
        print("\n---------< function response >----------")
        print(function_response)
        info_latest_price = function_response

        # Step 4: send the info on the function call and function response to GPT
        messages.append(response_message)  # extend conversation with assistant's reply
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response
        second_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
        )  # get a new response from GPT where it can see the function response

        print("\n---------< second response >----------")
        print(second_response)
        info_chat_response = second_response["choices"][0]["message"]["content"]

        info_result = {
            "ticker": info_ticker,
            "latest_price": info_latest_price,
            "chat_response": info_chat_response,
        }
        print("\n---------< response with function call >----------")
        print(info_result)

        return json.dumps(info_result)
    
    else:

        info_chat_response = response_message["content"]

        info_result = {
            "ticker": "",
            "latest_price": "",
            "chat_response": info_chat_response,
        }
        print("\n---------< response with no function call >----------")
        print(info_result)
        return json.dumps(info_result)





st.title("AI Stock data Chatbot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):

        # Run conversation
        coversation_result = json.loads(run_conversation(prompt))
        result_response = coversation_result.get("chat_response")
        result_ticker = coversation_result.get("ticker")
        result_price = coversation_result.get("latest_price")


        message_placeholder = st.empty()
        full_response = ""
        assistant_response = result_response



        # Simulate stream of response with milliseconds delay
        for chunk in assistant_response.split():
            full_response += chunk + " "
            time.sleep(0.05)
            # Add a blinking cursor to simulate typing
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})


    # =====< Additional temp data >=============================================

    # Display additional data
    if result_ticker != "":
        df = yf.Ticker(result_ticker).history(period="6mo", interval="1d")
        st.dataframe(df)

        # Display chart
        df = df.reset_index()
        df.columns = df.columns.str.lower()

        chart = StreamlitChart(width=640, height=300)
        chart.set(df)
        chart.watermark(result_ticker)
        chart.load()

