



###########################################################################################################
##               DONATIONS for NFI creator @iterativ                                                     ##
##                                                                                                       ##
##   Absolutely not required. However, will be accepted as a token of appreciation.                      ##
##                                                                                                       ##
##   BTC: bc1qvflsvddkmxh7eqhc4jyu5z5k6xcw3ay8jl49sk                                                     ##
##   ETH (ERC20): 0x83D3cFb8001BDC5d2211cBeBB8cB3461E5f7Ec91                                             ##
##   BEP20/BSC (ETH, BNB, ...): 0x86A0B21a20b39d16424B7c8003E4A7e12d78ABEe                               ##
##                                                                                                       ##
###########################################################################################################

import logging
import subprocess
import json
import random
import uuid
import typing

from aiogram import Bot, Dispatcher, executor, md, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified, Throttled

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode


# Configure logging
logging.basicConfig(level=logging.INFO)
API_TOKEN = 'XXXX:XXXXXXX'
# Initialize bot and dispatcher
data = {}
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


bots = {}
current_bot ={}
commands ={}
current_bot_id =0

# States
class holdOperation(StatesGroup):
    tradeID = State()  # Will be represented in storage as 'holdOperation:tradeID'
    profit  = State()  # Will be represented in storage as 'holdOperation:profit'
	
class unholdOperation(StatesGroup):
    tradeID = State()  # Will be represented in storage as 'unholdOperation:tradeID'
   
class UserStates(StatesGroup):
    current_bot = State() # Will be represented in storage as 'UserStates:current_bot'







def get_keyboard() -> types.ReplyKeyboardMarkup: #InlineKeyboardMarkup
    """
    Generate keyboard with list of posts
    """
    markup = types.ReplyKeyboardMarkup()
    
    for bot in data['bots']:
        markup.add(
            types.KeyboardButton(
                bot['name']),
        )
    return markup


def format_bots():
    text = md.text(
        md.hbold(current_bot['name']),
        md.quote_html(current_bot['exchange']),
        '',  # just new empty line
        sep='\n',
    )

    markup = types.ReplyKeyboardMarkup()
    markup.row(
        types.KeyboardButton('hold'), 
        types.KeyboardButton('unhold'), 
        types.KeyboardButton('show '+current_bot['name']+ ' holding'),       
    )
    
    #markup.row(
     #   types.KeyboardButton('profit'),
     #   types.KeyboardButton('status'),
     #   types.KeyboardButton('balance'),
    #)

    markup.row(
        types.KeyboardButton('stop'),
        types.KeyboardButton('reload_config'),
      
    )
    markup.add(types.KeyboardButton('<< Back'))
    return text, markup


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message, state: FSMContext):
    await types.ChatActions.typing()
    await UserStates.current_bot.set()
    await bot.send_message(data['chat_id'],'please choose one of your NFI Bots !', reply_markup=get_keyboard())

@dp.message_handler(Text(equals=['<< Back'], ignore_case=True))
async def BotsMainMenu(message: types.Message, state: FSMContext):
    await types.ChatActions.typing()
    await UserStates.current_bot.set()
    await bot.send_message(data['chat_id'],'please choose one of your NFI Bots !', reply_markup=get_keyboard())


async def exec_command( current_command_data :str ):
    Response = subprocess.check_output([f'python scripts/rest_client.py --config {current_bot["api_config_path"]} {current_command_data}'], shell=True)
    jsonResponse = json.loads(Response)
    return jsonResponse

@dp.message_handler(Text(equals=['reload_config',  'stop' ], ignore_case=True))
async def balance(message: types.Message, state: FSMContext):
    await types.ChatActions.typing()
    output=""
    jsonResponse = await exec_command(message.text) 
    logging.warning(  str(jsonResponse))
    await bot.send_message(data['chat_id'],jsonResponse)  
               
  




async def bot_view(bot_id: int ):
    global  current_bot
    current_bot=get_current_bot(bot_id)
    if current_bot is None:
        return await sendMessageToMe('unknown bot!')
    text, markup = format_bots()
    await bot.send_message(data['chat_id'],text, reply_markup=markup)

@dp.message_handler(state=UserStates.current_bot)
async def current_bot(message: types.Message, state: FSMContext) -> None:
    await types.ChatActions.typing()
    logging.warning("am on current_bot!")
    for t in data['bots'] :
        global  current_bot_id
        current_bot_id=int(t['id'])
        if t['name'] == message.text :
                async with state.proxy() as current_bot_data:
                    current_bot_data['current_bot'] = t['id']
                await state.finish()
                await bot_view(current_bot_data['current_bot'])
                break
        else:
                continue
          
@dp.message_handler(Text(contains=['holding'], ignore_case=True))
async def query_holding(message: types.Message , state: FSMContext):
    with open(current_bot["hold_tardes_path"]) as hold_trades_file:
        trades = json.load(hold_trades_file)
        #print(trades['trade_ids'])
        TextMessage = f"current holding for {current_bot['name']} at {current_bot['exchange']} :"+ '\n'
        for key in trades['trade_ids']:
            value = trades['trade_ids'][key]
            TextMessage=TextMessage+" tradeID : "+key+" Profit Ratio : "+str(value)+ '\n'
        await sendMessageToMe(TextMessage)


@dp.message_handler(Text(equals=['hold', 'unhold'], ignore_case=True))
async def query_bot_action(message: types.Message , state: FSMContext):
    await types.ChatActions.typing()
    bot = get_current_bot(current_bot_id)
    if bot is None:
        return await sendMessageToMe('unknown bot!')

    if message.text == 'hold':
        # Set state
        await holdOperation.tradeID.set()
        await sendMessageToMe("Hi there! please give me tardeID so your bot can hold it :) ")
    elif message.text == 'unhold':
        await unholdOperation.tradeID.set()
        await sendMessageToMe("Hi there! please give me tardeID so I can remove it :) ")

    
# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals=['cancel','<< Back'], ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await sendMessageToMe('Cancelled.')

@dp.message_handler(state=unholdOperation.tradeID)
async def process_tradeID_unhold(message: types.Message, state: FSMContext):
    """
    Process tradeID for unholding 
    """
    async with state.proxy() as unholding_data:
        unholding_data['tradeID'] = message.text
    await state.finish()

    with open(current_bot["hold_tardes_path"]) as unhold_trades_file:
        trades = json.load(unhold_trades_file)
        del trades['trade_ids'][unholding_data['tradeID']]


    with open(current_bot["hold_tardes_path"], 'w') as data_file:
        trades = json.dump(trades, data_file)   
    
    with open(current_bot["hold_tardes_path"]) as hold_trades_file:
        trades = json.load(hold_trades_file)
        #print(trades['trade_ids'])
        TextMessage = f"now current holding for {current_bot['name']} at {current_bot['exchange']} :"+ '\n'
        for key in trades['trade_ids']:
            value = trades['trade_ids'][key]
            TextMessage=TextMessage+" tradeID : "+key+" Profit Ratio : "+str(value)+ '\n'
        await sendMessageToMe(TextMessage)
    await bot_view(current_bot_id)   


@dp.message_handler(state=holdOperation.tradeID)
async def process_tradeID_hold(message: types.Message, state: FSMContext):
    """
    Process tradeID for holding 
    """
    async with state.proxy() as holding_data:
        holding_data['tradeID'] = message.text

    await holdOperation.next()
    await sendMessageToMe(" Profit Ratio ? ex: 5 (digits only / means 5%)")

# Check Profit Ratio. gotta be digit
@dp.message_handler(lambda message: not message.text.isdigit(), state=holdOperation.profit)
async def process_profit_invalid(message: types.Message):
    """
    If profit is invalid
    """
    return await sendMessageToMe("Profit Ratio must be a number.\nProfit Ratio ? ex: 5 (digits only / means 5%)")


@dp.message_handler(lambda message: message.text.isdigit(), state=holdOperation.profit)
async def process_profit(message: types.Message, state: FSMContext):
    # Update state and data
  
    async with state.proxy() as holding_data:
        holding_data['profit'] = int(message.text)
    # Finish conversation
    await state.finish()
    with open(current_bot["hold_tardes_path"]) as json_file:
        hold_trade = json.load(json_file)

    hold_trade['trade_ids'][holding_data['tradeID']] = holding_data['profit']/100
    print(hold_trade)
    with open(current_bot["hold_tardes_path"], 'w') as json_file:
        json.dump(hold_trade, json_file)    

    await sendMessageToMe( 
                "added tradeID :"+ holding_data['tradeID'] + '\n'+
                'with Profit Ratio :'+ str(holding_data['profit']/100))
    
    await bot_view(current_bot_id)


async def sendMessageToMe(text : Text):
    await bot.send_message(data['chat_id'],text)

@dp.errors_handler(exception=MessageNotModified)
async def message_not_modified_handler(update, error):
    return True # errors_handler must return True if error was handled correctly

@dp.message_handler()
async def text_handler(message:  types.Message):
    if message.text== 'ls':
        await bot.send_message(data['chat_id'],subprocess.check_output(["ls" , "-l"], shell=True))


def get_current_bot(id : int):
    for r in bots:
       if r['id']==id :
         return r
    return ""
def load_config():
    global data , bots
    logging.warning('loading config..')
    with open("config.json") as json_config_file:
        data = json.load(json_config_file)
        bots =data['bots']
        commands = data['commands']
    return data , bots , commands

if __name__ == '__main__':
    data , bots , commands= load_config()
    executor.start_polling(dp, skip_updates=True)