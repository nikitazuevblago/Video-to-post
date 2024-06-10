from aiogram.fsm.state import State, StatesGroup


class video_to_post_FORM(StatesGroup):
    tg_channel_id = State()


class create_project_FORM(StatesGroup):
    admin_group_id = State()
    tg_channel_id = State()


class new_channels_FORM(StatesGroup):
    new_YT_channels = State()