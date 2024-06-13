from os import getenv
import psycopg2
import pandas as pd
from tabulate import tabulate
try:
    from secret_key import HOST, DBNAME, USER, PASSWORD, PORT, CREATOR_ID, TESTER_ID, TEST_MODE
except:
    BOT_TOKEN = getenv('BOT_TOKEN')

    # DB env vars
    HOST = getenv('PGHOST')
    DBNAME = getenv('POSTGRES_DB')
    USER = getenv('PGUSER')
    PASSWORD = getenv('POSTGRES_PASSWORD')
    PORT = int(getenv('PGPORT'))
    CREATOR_ID = int(getenv('CREATOR_ID'))
    TESTER_ID = int(getenv('TESTER_ID'))
    TEST_MODE = int(getenv('TEST_MODE'))

# bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
from bot_settings import bot,dp


DB_config = {'host':HOST,'dbname':DBNAME,'user':USER,'password':PASSWORD,'port':PORT}

# FNs interacting with DB PostgreSQL
def get_projects_details(table_name='PROJECTS'): # project details - tg_channel, adming_group
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        try:
            cur.execute(f"""SELECT TG_channel_id, admin_group_id FROM {table_name};""")
            all_project_details_postgres = cur.fetchall()
            if len(all_project_details_postgres)>0:
                all_projects = {(row[0],row[1]) for row in all_project_details_postgres}
                return all_projects
            else:
                return []
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            bot.send_message(CREATOR_ID, f'[INFO] Table "{table_name}" does not exist...')
            raise ValueError(f'[INFO] Table "{table_name}" does not exist...')

    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while get_projects_details()')
    finally:
        cur.close()
        conn.close()


def get_tracked_channels(tg_channel_id, table_name='TRACKED_YT_CHANNELS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        try:
            cur.execute(f"""SELECT YT_channel_id FROM {table_name}
                            WHERE TG_CHANNEL_ID='{tg_channel_id}'
                        ;""")
            yt_channels_postgres = cur.fetchall()
            tracked_yt_channels = [channel_tuple[0] for channel_tuple in yt_channels_postgres]
            return tracked_yt_channels
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            bot.send_message(CREATOR_ID, f'[INFO] Table "{table_name}" does not exist...')
            raise ValueError(f'[INFO] Table "{table_name}" does not exist...')
            

    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while get_tracked_yt_creators()')
    finally:
        cur.close()
        conn.close()


def remove_yt_creators(bad_channels, table_name='TRACKED_YT_CHANNELS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        for channel in bad_channels:
            cur.execute(f"""DELETE FROM {table_name} WHERE channel = '{channel}';""")
            conn.commit()

    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while remove_yt_creators()')
    finally:
        cur.close()
        conn.close()


def get_used_video_urls(table_name='USED_VIDEO_URLS') -> set:
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        try:
            cur.execute(f"""SELECT video_url FROM {table_name};""")
            video_urls_postgres = cur.fetchall()
            used_video_urls = {url_tuple[0] for url_tuple in video_urls_postgres}
            return used_video_urls
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            bot.send_message(CREATOR_ID, f'[INFO] Table "{table_name}" does not exist...') 
            raise ValueError(f'[INFO] Table "{table_name}" does not exist...')
            
    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while get_used_video_urls()')
    finally:
        cur.close()
        conn.close()


def insert_new_video_urls(new_video_urls, table_name='USED_VIDEO_URLS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        for video_url in new_video_urls:
            try:
                cur.execute(f"""INSERT INTO {table_name} (video_url) VALUES ('{video_url}');""")
                conn.commit()
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                bot.send_message(CREATOR_ID, f'[INFO] Video_url {video_url} already exists in DB!')
            except psycopg2.errors.UndefinedTable:
                conn.rollback()
                bot.send_message(CREATOR_ID, f'[INFO] Table "{table_name}" does not exist...')
                raise ValueError(f'[INFO] Table "{table_name}" does not exist...')

    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while insert_new_video_urls()')
    finally:
        cur.close()
        conn.close()


def clear_up_db():
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        tables_to_drop = ['USED_VIDEO_URLS','TRACKED_YT_CHANNELS','TRANSACTIONS','USERS','POST_CONFIG','PROJECTS','PENDING_WORK']
        for table in tables_to_drop:
            try:
                cur.execute(f"""DROP TABLE {table};""")
                conn.commit()
            except psycopg2.errors.UndefinedTable:
                conn.rollback()

    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while clear_up_db()')
    
    finally:
        cur.close()
        conn.close()


def create_db():
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        cur.execute(f"""CREATE TABLE IF NOT EXISTS USED_VIDEO_URLS (
                                video_url VARCHAR(255) PRIMARY KEY);""")
        conn.commit()
        

        cur.execute(f"""CREATE TABLE IF NOT EXISTS PROJECTS (
                            TG_channel_name VARCHAR(25) UNIQUE,
                            admin_group_id BIGINT,
                            TG_channel_id BIGINT PRIMARY KEY);""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS POST_CONFIG (
                            TG_channel_id BIGINT REFERENCES PROJECTS(TG_channel_id) ON DELETE CASCADE,
                            lang VARCHAR(5),
                            reference_creator BOOLEAN,
                            img BOOLEAN);""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS TRACKED_YT_CHANNELS (
                            YT_channel_id VARCHAR(50),
                            TG_channel_id BIGINT REFERENCES PROJECTS(TG_channel_id) ON DELETE CASCADE,
                            PRIMARY KEY (YT_channel_id, TG_channel_id));""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS USERS (
                                user_id BIGINT PRIMARY KEY,
                                lang VARCHAR(5),
                                balance BIGINT
                    );""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS TRANSACTIONS (
                                transaction_id SERIAL PRIMARY KEY,
                                user_id BIGINT,
                                sum FLOAT,
                                date TIMESTAMP,
                                action VARCHAR(10)
                    );""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS PENDING_WORK (
                                timestamp_str VARCHAR(50) PRIMARY KEY,
                                video_url VARCHAR(250),
                                post_cost BIGINT,
                                admin_group_id BIGINT,
                                tg_channel_id BIGINT
                    );""")
        conn.commit()


    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while create_db()')
    
    finally:
        cur.close()
        conn.close()


def insert_new_project(TG_channel_name, admin_group_id, tg_channel_id, table_name='PROJECTS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        try:
            cur.execute(f"""INSERT INTO {table_name} (TG_channel_name, admin_group_id, TG_channel_id) VALUES ('{TG_channel_name}',{admin_group_id},{tg_channel_id});""")
            conn.commit()
            return True
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            print(f'[ERROR] Table {table_name} does not exist!')
            return False
        
        except psycopg2.errors.NumericValueOutOfRange:
            conn.rollback()
            print('[ERROR] Letters in BIGINT column!')
            return False
        
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            print(f'[ERROR] Project with id "{tg_channel_id}" already exists!')
            return False

    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while insert_new_project()')
        return False

    except psycopg2.errors.UndefinedColumn:
        return False
    
    finally:
        cur.close()
        conn.close()


def load_dummy_data():
    # PROJECTS table
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        try:
            cur.execute(f"""INSERT INTO PROJECTS (TG_channel_name, admin_group_id, TG_channel_id) VALUES ('Become a Millionaire',-1002237753557,-1002169269607);""")
            conn.commit()
            cur.execute(f"""INSERT INTO POST_CONFIG (TG_channel_id, lang, reference_creator, img) VALUES (-1002169269607,'ru',False,True);""")
            conn.commit()
            # cur.execute(f"""INSERT INTO USERS (user_id, lang, balance, img) VALUES (-1002169269607,'en',False,True);""")
            # conn.commit()
            return True
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            print(f'[ERROR] Table PROJECTS does not exist!')
            return False
        
        except psycopg2.errors.NumericValueOutOfRange:
            conn.rollback()
            print('[ERROR] Letters in BIGINT column!')
            return False

    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while load_dummy_data()')
        return False

    except psycopg2.errors.UndefinedColumn:
        return False
    
    finally:
        cur.close()
        conn.close()


def get_admin_group_ids():
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        # Check if the command /new_channels executes in admin_group
        cur.execute("""SELECT admin_group_id FROM PROJECTS""")
        admin_group_ids_postgres = cur.fetchall()
        admin_group_ids = {channel_tuple[0] for channel_tuple in admin_group_ids_postgres}
        return admin_group_ids
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while get_admin_group_ids()')
        return {}
    finally:
        cur.close()
        conn.close()


def get_related_tg_channels(admin_group_id, table_name='PROJECTS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        cur.execute(f"""SELECT TG_CHANNEL_ID FROM {table_name} WHERE admin_group_id={admin_group_id}""")
        related_tg_channels_ids_postgres = cur.fetchall()
        if len(related_tg_channels_ids_postgres)>0:
            related_tg_channels_ids = [row[0] for row in related_tg_channels_ids_postgres]
            return related_tg_channels_ids
        else:
            return []
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while get_related_tg_channels()')
        return []
    finally:
        cur.close()
        conn.close()


def link_new_YT_channels(TG_channel_id, new_YT_channels, table_name='TRACKED_YT_CHANNELS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        for new_YT_channel in new_YT_channels:
            cur.execute(f"""INSERT INTO {table_name} (YT_channel_id, TG_channel_id) VALUES ('{new_YT_channel}',{TG_channel_id})""")
            conn.commit()
        return True
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while insert_new_yt_creators()')
        return False
    
    finally:
        cur.close()
        conn.close()


# This function is used for creating new user and for changing the user's details 
def create_or_update_user(user_id, lang=None, balance=None, default=False, table_name='USERS'):
    # Set default user config
    if default:
        lang = 'ru'
        balance = 0
    
    if user_id in [CREATOR_ID, TESTER_ID] and TEST_MODE==0: 
        balance = 5000
    
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        # Check if the user exists
        cur.execute(f"""SELECT * FROM {table_name} WHERE user_id = {user_id}""")
        user_row_postgres = cur.fetchall()
        if len(user_row_postgres)==0:
            cur.execute(f"""INSERT INTO {table_name} (user_id, lang, balance) VALUES ({user_id}, '{lang}', {balance});""")
        else:
            if default:
                return True
            if lang==None:
                lang = user_row_postgres[0][1]
            if balance==None:
                balance = user_row_postgres[0][2]

            cur.execute(f"""UPDATE {table_name} SET lang='{lang}', balance={balance} WHERE user_id = {user_id};""")

        conn.commit()
        return True
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while create_new_user()')
        return False
    
    finally:
        cur.close()
        conn.close()


def get_user_balance(user_id, table_name='USERS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        # Check if the user exists
        cur.execute(f"""SELECT balance FROM {table_name} WHERE user_id = {user_id}""")
        balance = cur.fetchall()[0][0]

        return balance
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while create_new_user()')
    
    finally:
        cur.close()
        conn.close()


def add_new_transaction(user_id, sum, action, table_name='TRANSACTIONS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        # SQL query to get the current timestamp in Moscow timezone
        cur.execute("SELECT current_timestamp AT TIME ZONE 'Europe/Moscow';")
        current_moscow_time = cur.fetchone()[0].strftime('%Y-%m-%d %H:%M:%S')

        # CURRENT_TIMESTAMP will be current dependent on server's time!!! Railway default is OREGON, USA
        cur.execute(f"""INSERT INTO {table_name} (user_id, sum, date, action) VALUES({user_id}, {sum}, '{current_moscow_time}', '{action}');""")
        conn.commit()
        
        return True
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while create_new_user()')
        return False
    
    finally:
        cur.close()
        conn.close()


def get_user_transactions(user_id, table_name='TRANSACTIONS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        # CURRENT_TIMESTAMP will be current dependent on server's time!!! Railway default is OREGON, USA
        cur.execute(f"""SELECT * FROM {table_name} WHERE user_id = {user_id};""")
        user_transactions_postgres = cur.fetchall()
        if len(user_transactions_postgres)>0:
            user_transactions_table = pd.DataFrame(user_transactions_postgres,columns=['transaction_id','user_id','sum','date','action'])
            str_table = tabulate(user_transactions_table, headers='keys', tablefmt='pipe')
            return f"```\n{str_table}\n```"
        else:
            return "You don't have any transactions yet!"
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while create_new_user()')
        return False
    
    finally:
        cur.close()
        conn.close()


def create_or_update_config(TG_channel_id, lang=None, reference=None, img=None, default=False, table_name='POST_CONFIG'):

    # Set default user config
    if default:
        lang = 'en'
        reference = False
        img = True

    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        
        # Check if the user exists
        cur.execute(f"""SELECT * FROM {table_name} WHERE TG_channel_id = {TG_channel_id}""")
        tg_config_row = cur.fetchall()
        if len(tg_config_row)==0:
            cur.execute(f"""INSERT INTO {table_name} (TG_channel_id, lang, reference_creator, img) VALUES ({TG_channel_id}, '{lang}', {reference}, {img});""")
        else:
            if default:
                return True
            if lang==None:
                lang = tg_config_row[0][1]
            if reference==None:
                reference = tg_config_row[0][2]
            if img==None:
                img = img[0][3]

            cur.execute(f"""UPDATE {table_name} SET lang='{lang}', reference_creator={reference}, img={img} WHERE TG_channel_id = {TG_channel_id};""")

        conn.commit()
        return True
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while create_or_update_config()')
        return False
    
    finally:
        cur.close()
        conn.close()


def get_projects(admin_group_id, table_name='PROJECTS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        cur.execute(f"""SELECT tg_channel_name FROM {table_name} WHERE admin_group_id = {admin_group_id};""")
        linked_projects_postgres = cur.fetchall()
        if len(linked_projects_postgres)>0:
           linked_projects = [row[0] for row in linked_projects_postgres]
           return linked_projects
        else:
            return []
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while get_projects()')
        return False
    
    finally:
        cur.close()
        conn.close()
    

def get_post_config(TG_channel_id, table_name='POST_CONFIG'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        cur.execute(f"""SELECT lang, reference_creator, img FROM {table_name} WHERE TG_channel_id = {TG_channel_id};""")
        tg_channel_config_postgres = cur.fetchall()
        config_lang, config_reference, img = tg_channel_config_postgres[0]
        return config_lang, config_reference, img
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while get_post_config()')
        return False
    
    finally:
        cur.close()
        conn.close()


def get_user_lang(user_id, table_name='USERS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        cur.execute(f"""SELECT lang FROM {table_name} WHERE user_id = {user_id};""")
        user_row_postgres = cur.fetchall()
        try:
            lang = user_row_postgres[0][0]
            return lang
        except:
            create_or_update_user(user_id,default=True)
            cur.execute(f"""SELECT lang FROM {table_name} WHERE user_id = {user_id};""")
            user_row_postgres = cur.fetchall()
            try:
                lang = user_row_postgres[0][0]
                return lang
            except:
                raise ValueError("Could not get the user's language!")
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while get_user_lang()')
        return False
    
    finally:
        cur.close()
        conn.close()


def new_pending_work(timestamp_str, video_url, post_cost, admin_group_id, tg_channel_id, table_name='PENDING_WORK'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        cur.execute(f"""INSERT INTO {table_name} (video_url, post_cost, admin_group_id, tg_channel_id, timestamp_str) 
                    VALUES ('{video_url}', {post_cost}, {admin_group_id}, {tg_channel_id}, '{timestamp_str}');""")
        conn.commit()
        return True
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while new_pending_work()')
        return False
    
    finally:
        cur.close()
        conn.close()


def get_pendind_work_details(timestamp_str, table_name='PENDING_WORK'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        cur.execute(f"""SELECT * FROM {table_name} WHERE timestamp_str = '{timestamp_str}';""")
        pending_work_row = cur.fetchall()
        timestamp_str, video_url, post_cost, admin_group_id, tg_channel_id = pending_work_row[0]
        return timestamp_str, video_url, post_cost, admin_group_id, tg_channel_id
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while get_pendind_work_details()')
        return False
    
    finally:
        cur.close()
        conn.close()


def delete_pending_work(timestamp_str, table_name='PENDING_WORK'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()

        cur.execute(f"""DELETE FROM {table_name} WHERE timestamp_str = '{timestamp_str}';;""")
        conn.commit()
        return True
        
    
    except psycopg2.errors.OperationalError:
        print('ERROR: cannot connect to PostgreSQL while delete_pending_work()')
        return False
    
    finally:
        cur.close()
        conn.close()
    

# Not really works with my DB but works with TG DB, so...
from aiogram.types import ChatMemberOwner
async def get_chat_owner_id(chat_id):
    chat_administrators = await bot.get_chat_administrators(chat_id)
    for admin in chat_administrators:
        if isinstance(admin, ChatMemberOwner):
            owner_id = admin.user.id
            return owner_id
    raise ValueError('Could not find the owner :(')
