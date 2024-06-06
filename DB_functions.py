from os import getenv
import psycopg2
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram import Bot
try:
    from secret_key import HOST, DBNAME, USER, PASSWORD, PORT, CREATOR_ID, BOT_TOKEN
except:
    BOT_TOKEN = getenv('BOT_TOKEN')

    # DB env vars
    HOST = getenv('PGHOST')
    DBNAME = getenv('POSTGRES_DB')
    USER = getenv('PGUSER')
    PASSWORD = getenv('POSTGRES_PASSWORD')
    PORT = int(getenv('PGPORT'))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

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
            tracked_yt_channels = {channel_tuple[0] for channel_tuple in yt_channels_postgres}
            return tracked_yt_channels
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            bot.send_message(CREATOR_ID, f'[INFO] Table "{table_name}" does not exist...')
            # cur.execute(f"""CREATE TABLE IF NOT EXISTS {table_name} (
            #                 channel VARCHAR(255) PRIMARY KEY);""")
            # default_channels = ['imangadzhi','noahkagan']
            # for channel in default_channels:
            #     cur.execute(f"""INSERT INTO {table_name} (channel) VALUES ('{channel}');""")
            #     conn.commit()
            # return default_channels
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
        tables_to_drop = ['USED_VIDEO_URLS','TRACKED_YT_CHANNELS','PROJECT_ADMINS','PROJECTS','TRANSACTIONS','USERS']
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
        #tables_to_create = ['USED_VIDEO_URLS','TRACKED_YT_CHANNELS','PROJECT_ADMINS','PROJECTS','TRANSACTIONS','USERS']
        cur.execute(f"""CREATE TABLE IF NOT EXISTS USED_VIDEO_URLS (
                                video_url VARCHAR(255) PRIMARY KEY);""")
        conn.commit()
        # cur.execute(f"""CREATE TABLE IF NOT EXISTS PROJECT_ADMINS (
        #                     TG_channel_id INT REFERENCES PROJECTS(TG_channel_id) ON DELETE CASCADE,
        #                     user_id INT REFERENCES USERS(user_id) ON DELETE CASCADE,       
        #             );""")

        cur.execute(f"""CREATE TABLE IF NOT EXISTS PROJECTS (
                            project_name VARCHAR(25) UNIQUE,
                            admin_group_id INT,
                            TG_channel_id INT PRIMARY KEY);""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS TRACKED_YT_CHANNELS (
                            YT_channel_id INT PRIMARY KEY,
                            TG_channel_id INT REFERENCES PROJECTS(TG_channel_id) ON DELETE CASCADE);""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS USERS (
                                user_id INT PRIMARY KEY,
                                lang VARCHAR(5),
                                balance INT
                    );""")
        conn.commit()

        cur.execute(f"""CREATE TABLE IF NOT EXISTS TRANSACTIONS (
                                transaction_id INT PRIMARY KEY,
                                user_id INT,
                                sum FLOAT,
                                date TIMESTAMP
                    );""")
        conn.commit()


    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while create_db()')
    
    finally:
        cur.close()
        conn.close()


def insert_new_project(project_name, admin_group_id, tg_channel_id, table_name='PROJECTS'):
    try:
        # Establish db connection
        conn = psycopg2.connect(**DB_config)
        cur = conn.cursor()
        try:
            cur.execute(f"""INSERT INTO {table_name} (project_name, admin_group_id, TG_channel_id) VALUES ('{project_name}','{admin_group_id}','{tg_channel_id}');""")
            conn.commit()
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            raise ValueError(f'Table {table_name} does not exist!')

    except psycopg2.errors.OperationalError:
        raise('ERROR: cannot connect to PostgreSQL while insert_new_project()')
    
    finally:
        cur.close()
        conn.close()