import json
import logging
import time
from typing import Optional


from open_webui.socket.main import get_event_emitter
from open_webui.internal.db import get_db
from open_webui.models.chats import (
    ChatForm,
    ChatImportForm,
    ChatResponse,
    Chats,
    ChatTitleIdResponse,
    Chat,
    ChatModel,
)
from open_webui.models.tags import TagModel, Tags, TagForm
from open_webui.models.folders import Folders

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.utils.models import get_available_models
import requests

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetChatList
############################


@router.get("/", response_model=list[ChatTitleIdResponse])
@router.get("/list", response_model=list[ChatTitleIdResponse])
async def get_session_user_chat_list(
    user=Depends(get_verified_user), page: Optional[int] = None
):
    try:
        if page is not None:
            limit = 60
            skip = (page - 1) * limit

            return Chats.get_chat_title_id_list_by_user_id(
                user.id, skip=skip, limit=limit
            )
        else:
            return Chats.get_chat_title_id_list_by_user_id(user.id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteAllChats
############################


@router.delete("/", response_model=bool)
async def delete_all_user_chats(request: Request, user=Depends(get_verified_user)):

    if user.role == "user" and not has_permission(
        user.id, "chat.delete", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Chats.delete_chats_by_user_id(user.id)
    return result


############################
# GetUserChatList
############################


@router.get("/list/user/{user_id}", response_model=list[ChatTitleIdResponse])
async def get_user_chat_list_by_user_id(
    user_id: str,
    page: Optional[int] = None,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    user=Depends(get_admin_user),
):
    if not ENABLE_ADMIN_CHAT_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    return Chats.get_chat_list_by_user_id(
        user_id, include_archived=True, filter=filter, skip=skip, limit=limit
    )


############################
# CreateNewChat
############################


@router.post("/new", response_model=Optional[ChatResponse])
async def create_new_chat(form_data: ChatForm, user=Depends(get_verified_user)):
    try:
        chat = Chats.insert_new_chat(user.id, form_data)
        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ImportChat
############################


@router.post("/import", response_model=Optional[ChatResponse])
async def import_chat(form_data: ChatImportForm, user=Depends(get_verified_user)):
    try:
        chat = Chats.import_chat(user.id, form_data)
        if chat:
            tags = chat.meta.get("tags", [])
            for tag_id in tags:
                tag_id = tag_id.replace(" ", "_").lower()
                tag_name = " ".join([word.capitalize() for word in tag_id.split("_")])
                if (
                    tag_id != "none"
                    and Tags.get_tag_by_name_and_user_id(tag_name, user.id) is None
                ):
                    Tags.insert_new_tag(tag_name, user.id)

        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChats
############################


@router.get("/search", response_model=list[ChatTitleIdResponse])
async def search_user_chats(
    text: str, page: Optional[int] = None, user=Depends(get_verified_user)
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    chat_list = [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_user_id_and_search_text(
            user.id, text, skip=skip, limit=limit
        )
    ]

    # Delete tag if no chat is found
    words = text.strip().split(" ")
    if page == 1 and len(words) == 1 and words[0].startswith("tag:"):
        tag_id = words[0].replace("tag:", "")
        if len(chat_list) == 0:
            if Tags.get_tag_by_name_and_user_id(tag_id, user.id):
                log.debug(f"deleting tag: {tag_id}")
                Tags.delete_tag_by_name_and_user_id(tag_id, user.id)

    return chat_list


############################
# GetChatsByFolderId
############################


@router.get("/folder/{folder_id}", response_model=list[ChatResponse])
async def get_chats_by_folder_id(folder_id: str, user=Depends(get_verified_user)):
    folder_ids = [folder_id]
    children_folders = Folders.get_children_folders_by_id_and_user_id(
        folder_id, user.id
    )
    if children_folders:
        folder_ids.extend([folder.id for folder in children_folders])

    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_folder_ids_and_user_id(folder_ids, user.id)
    ]


############################
# GetPinnedChats
############################


@router.get("/pinned", response_model=list[ChatTitleIdResponse])
async def get_user_pinned_chats(user=Depends(get_verified_user)):
    return [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_pinned_chats_by_user_id(user.id)
    ]


############################
# GetChats
############################


@router.get("/all", response_model=list[ChatResponse])
async def get_user_chats(user=Depends(get_verified_user)):
    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_user_id(user.id)
    ]


############################
# GetArchivedChats
############################


@router.get("/all/archived", response_model=list[ChatResponse])
async def get_user_archived_chats(user=Depends(get_verified_user)):
    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_archived_chats_by_user_id(user.id)
    ]


############################
# GetAllTags
############################


@router.get("/all/tags", response_model=list[TagModel])
async def get_all_user_tags(user=Depends(get_verified_user)):
    try:
        tags = Tags.get_tags_by_user_id(user.id)
        return tags
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetAllChatsInDB
############################


@router.get("/all/db", response_model=list[ChatResponse])
async def get_all_user_chats_in_db(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return [ChatResponse(**chat.model_dump()) for chat in Chats.get_chats()]


############################
# GetArchivedChats
############################


@router.get("/archived", response_model=list[ChatTitleIdResponse])
async def get_archived_session_user_chat_list(
    page: Optional[int] = None,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    user=Depends(get_verified_user),
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    chat_list = [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_archived_chat_list_by_user_id(
            user.id,
            filter=filter,
            skip=skip,
            limit=limit,
        )
    ]

    return chat_list


############################
# ArchiveAllChats
############################


@router.post("/archive/all", response_model=bool)
async def archive_all_chats(user=Depends(get_verified_user)):
    return Chats.archive_all_chats_by_user_id(user.id)


############################
# GetSharedChatById
############################


@router.get("/share/{share_id}", response_model=Optional[ChatResponse])
async def get_shared_chat_by_id(share_id: str, user=Depends(get_verified_user)):
    if user.role == "pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role == "user" or (user.role == "admin" and not ENABLE_ADMIN_CHAT_ACCESS):
        chat = Chats.get_chat_by_share_id(share_id)
    elif user.role == "admin" and ENABLE_ADMIN_CHAT_ACCESS:
        chat = Chats.get_chat_by_id(share_id)

    if chat:
        return ChatResponse(**chat.model_dump())

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# GetChatsByTags
############################


class TagForm(BaseModel):
    name: str


class TagFilterForm(TagForm):
    skip: Optional[int] = 0
    limit: Optional[int] = 50


@router.post("/tags", response_model=list[ChatTitleIdResponse])
async def get_user_chat_list_by_tag_name(
    form_data: TagFilterForm, user=Depends(get_verified_user)
):
    chats = Chats.get_chat_list_by_user_id_and_tag_name(
        user.id, form_data.name, form_data.skip, form_data.limit
    )
    if len(chats) == 0:
        Tags.delete_tag_by_name_and_user_id(form_data.name, user.id)

    return chats


############################
# GetChatById
############################


@router.get("/{id}", response_model=Optional[ChatResponse])
async def get_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)

    if chat:
        return ChatResponse(**chat.model_dump())

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# UpdateChatById
############################


@router.post("/{id}", response_model=Optional[ChatResponse])
async def update_chat_by_id(
    id: str, form_data: ChatForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        updated_chat = {**chat.chat, **form_data.chat}
        chat = Chats.update_chat_by_id(id, updated_chat)
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# UpdateChatMessageById
############################
class MessageForm(BaseModel):
    content: str


@router.post("/{id}/messages/{message_id}", response_model=Optional[ChatResponse])
async def update_chat_message_by_id(
    id: str, message_id: str, form_data: MessageForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id(id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if chat.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chat = Chats.upsert_message_to_chat_by_id_and_message_id(
        id,
        message_id,
        {
            "content": form_data.content,
        },
    )

    event_emitter = get_event_emitter(
        {
            "user_id": user.id,
            "chat_id": id,
            "message_id": message_id,
        },
        False,
    )

    if event_emitter:
        await event_emitter(
            {
                "type": "chat:message",
                "data": {
                    "chat_id": id,
                    "message_id": message_id,
                    "content": form_data.content,
                },
            }
        )

    return ChatResponse(**chat.model_dump())


############################
# SendChatMessageEventById
############################
class EventForm(BaseModel):
    type: str
    data: dict


@router.post("/{id}/messages/{message_id}/event", response_model=Optional[bool])
async def send_chat_message_event_by_id(
    id: str, message_id: str, form_data: EventForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id(id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if chat.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    event_emitter = get_event_emitter(
        {
            "user_id": user.id,
            "chat_id": id,
            "message_id": message_id,
        }
    )

    try:
        if event_emitter:
            await event_emitter(form_data.model_dump())
        else:
            return False
        return True
    except:
        return False


############################
# DeleteChatById
############################


@router.delete("/{id}", response_model=bool)
async def delete_chat_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        chat = Chats.get_chat_by_id(id)
        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id) == 1:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        result = Chats.delete_chat_by_id(id)

        return result
    else:
        if not has_permission(
            user.id, "chat.delete", request.app.state.config.USER_PERMISSIONS
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

        chat = Chats.get_chat_by_id(id)
        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id) == 1:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        result = Chats.delete_chat_by_id_and_user_id(id, user.id)
        return result


############################
# GetPinnedStatusById
############################


@router.get("/{id}/pinned", response_model=Optional[bool])
async def get_pinned_status_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        return chat.pinned
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# PinChatById
############################


@router.post("/{id}/pin", response_model=Optional[ChatResponse])
async def pin_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        chat = Chats.toggle_chat_pinned_by_id(id)
        return chat
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CloneChat
############################


class CloneForm(BaseModel):
    title: Optional[str] = None


@router.post("/{id}/clone", response_model=Optional[ChatResponse])
async def clone_chat_by_id(
    form_data: CloneForm, id: str, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        updated_chat = {
            **chat.chat,
            "originalChatId": chat.id,
            "branchPointMessageId": chat.chat["history"]["currentId"],
            "title": form_data.title if form_data.title else f"Clone of {chat.title}",
        }

        chat = Chats.insert_new_chat(user.id, ChatForm(**{"chat": updated_chat}))
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CloneSharedChatById
############################


@router.post("/{id}/clone/shared", response_model=Optional[ChatResponse])
async def clone_shared_chat_by_id(id: str, user=Depends(get_verified_user)):

    if user.role == "admin":
        chat = Chats.get_chat_by_id(id)
    else:
        chat = Chats.get_chat_by_share_id(id)

    if chat:
        updated_chat = {
            **chat.chat,
            "originalChatId": chat.id,
            "branchPointMessageId": chat.chat["history"]["currentId"],
            "title": f"Clone of {chat.title}",
        }

        chat = Chats.insert_new_chat(user.id, ChatForm(**{"chat": updated_chat}))
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ArchiveChat
############################


@router.post("/{id}/archive", response_model=Optional[ChatResponse])
async def archive_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        chat = Chats.toggle_chat_archive_by_id(id)

        # Delete tags if chat is archived
        if chat.archived:
            for tag_id in chat.meta.get("tags", []):
                if Chats.count_chats_by_tag_name_and_user_id(tag_id, user.id) == 0:
                    log.debug(f"deleting tag: {tag_id}")
                    Tags.delete_tag_by_name_and_user_id(tag_id, user.id)
        else:
            for tag_id in chat.meta.get("tags", []):
                tag = Tags.get_tag_by_name_and_user_id(tag_id, user.id)
                if tag is None:
                    log.debug(f"inserting tag: {tag_id}")
                    tag = Tags.insert_new_tag(tag_id, user.id)

        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ShareChatById
############################


@router.post("/{id}/share", response_model=Optional[ChatResponse])
async def share_chat_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if (user.role != "admin") and (
        not has_permission(
            user.id, "chat.share", request.app.state.config.USER_PERMISSIONS
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chat = Chats.get_chat_by_id_and_user_id(id, user.id)

    if chat:
        if chat.share_id:
            shared_chat = Chats.update_shared_chat_by_chat_id(chat.id)
            return ChatResponse(**shared_chat.model_dump())

        shared_chat = Chats.insert_shared_chat_by_chat_id(chat.id)
        if not shared_chat:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
        return ChatResponse(**shared_chat.model_dump())

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# DeletedSharedChatById
############################


@router.delete("/{id}/share", response_model=Optional[bool])
async def delete_shared_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        if not chat.share_id:
            return False

        result = Chats.delete_shared_chat_by_chat_id(id)
        update_result = Chats.update_chat_share_id_by_id(id, None)

        return result and update_result != None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# UpdateChatFolderIdById
############################


class ChatFolderIdForm(BaseModel):
    folder_id: Optional[str] = None


@router.post("/{id}/folder", response_model=Optional[ChatResponse])
async def update_chat_folder_id_by_id(
    id: str, form_data: ChatFolderIdForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        chat = Chats.update_chat_folder_id_by_id_and_user_id(
            id, user.id, form_data.folder_id
        )
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChatTagsById
############################


@router.get("/{id}/tags", response_model=list[TagModel])
async def get_chat_tags_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# AddChatTagById
############################


@router.post("/{id}/tags", response_model=list[TagModel])
async def add_tag_by_id_and_tag_name(
    id: str, form_data: TagForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        tags = chat.meta.get("tags", [])
        tag_id = form_data.name.replace(" ", "_").lower()

        if tag_id == "none":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Tag name cannot be 'None'"),
            )

        if tag_id not in tags:
            Chats.add_chat_tag_by_id_and_user_id_and_tag_name(
                id, user.id, form_data.name
            )

        chat = Chats.get_chat_by_id_and_user_id(id, user.id)
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteChatTagById
############################


@router.delete("/{id}/tags", response_model=list[TagModel])
async def delete_tag_by_id_and_tag_name(
    id: str, form_data: TagForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        Chats.delete_tag_by_id_and_user_id_and_tag_name(id, user.id, form_data.name)

        if Chats.count_chats_by_tag_name_and_user_id(form_data.name, user.id) == 0:
            Tags.delete_tag_by_name_and_user_id(form_data.name, user.id)

        chat = Chats.get_chat_by_id_and_user_id(id, user.id)
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# DeleteAllTagsById
############################


@router.delete("/{id}/tags/all", response_model=Optional[bool])
async def delete_all_tags_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        Chats.delete_all_tags_by_id_and_user_id(id, user.id)

        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id) == 0:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        return True
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# ChatSummaryForm
############################


class ChatSummaryForm(BaseModel):
    subject: Optional[str] = None
    knowledge_points: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class ChatSummaryResponse(BaseModel):
    subject: str
    knowledge_points: list[str]
    summary: str


############################
# SummarizeChatById
############################


@router.post("/{id}/summarize", response_model=ChatSummaryResponse)
async def summarize_chat_by_id(id: str, user=Depends(get_verified_user)):
    """
    使用AI自动总结聊天内容，提取科目分类和知识点
    """
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )
    
    # 提取聊天消息内容
    messages = chat.chat.get("history", {}).get("messages", {})
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages found in chat"
        )
    
    # 构建聊天内容摘要
    chat_content = []
    for msg_id, message in messages.items():
        if message.get("role") in ["user", "assistant"]:
            content = message.get("content", "")
            if isinstance(content, str):
                chat_content.append(f"{message.get('role', 'unknown')}: {content}")
    
    chat_text = "\n".join(chat_content)
    
    # 创建总结prompt
    summary_prompt = f"""请分析以下对话内容，并提供：
1. 主要科目分类（如：数学、物理、化学、语文、英语、历史、地理、生物、政治、计算机科学等）
2. 具体知识点列表（3-5个关键知识点）
3. 对话内容的简要总结

对话内容：
{chat_text}

请用JSON格式回复，包含以下字段：
- subject: 主要科目
- knowledge_points: 知识点数组
- summary: 内容总结
"""
    
    try:
        # 这里应该调用AI模型进行总结，暂时返回模拟数据
        # 在实际部署时，需要集成Gemini API或其他AI服务
        
        # 简单的关键词匹配来确定科目
        subject = "通用"
        knowledge_points = ["问题解答", "知识讨论"]
        
        # 基于内容长度生成简单总结
        word_count = len(chat_text)
        if word_count < 100:
            summary = "简短对话"
        elif word_count < 500:
            summary = "中等长度的知识讨论"
        else:
            summary = "详细的学习交流"
        
        # 基于关键词推断科目
        if any(keyword in chat_text.lower() for keyword in ["数学", "计算", "方程", "函数", "几何"]):
            subject = "数学"
            knowledge_points = ["计算题", "方程求解", "函数分析"]
        elif any(keyword in chat_text.lower() for keyword in ["物理", "力学", "电学", "光学"]):
            subject = "物理"
            knowledge_points = ["物理概念", "公式应用", "实验分析"]
        elif any(keyword in chat_text.lower() for keyword in ["化学", "反应", "元素", "分子"]):
            subject = "化学"
            knowledge_points = ["化学反应", "元素周期表", "分子结构"]
        elif any(keyword in chat_text.lower() for keyword in ["语文", "作文", "文学", "古诗"]):
            subject = "语文"
            knowledge_points = ["文学鉴赏", "写作技巧", "古典文学"]
        elif any(keyword in chat_text.lower() for keyword in ["英语", "english", "单词", "语法"]):
            subject = "英语"
            knowledge_points = ["词汇学习", "语法规则", "阅读理解"]
        
        return ChatSummaryResponse(
            subject=subject,
            knowledge_points=knowledge_points,
            summary=summary
        )
        
    except Exception as e:
        log.error(f"Error summarizing chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to summarize chat"
        )


############################
# UpdateChatSummaryById
############################


@router.post("/{id}/summary", response_model=Optional[ChatResponse])
async def update_chat_summary_by_id(
    id: str, form_data: ChatSummaryForm, user=Depends(get_verified_user)
):
    """
    更新聊天的科目、知识点和标签信息
    """
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )
    
    try:
        with get_db() as db:
            chat_record = db.get(Chat, id)
            
            # 更新meta字段
            updated_meta = {**chat_record.meta}
            
            if form_data.subject is not None:
                updated_meta["subject"] = form_data.subject
            
            if form_data.knowledge_points is not None:
                updated_meta["knowledge_points"] = form_data.knowledge_points
            
            if form_data.tags is not None:
                # 处理标签更新
                old_tags = set(updated_meta.get("tags", []))
                new_tags = set([tag.replace(" ", "_").lower() for tag in form_data.tags])
                
                # 删除旧标签
                for tag in old_tags - new_tags:
                    if Chats.count_chats_by_tag_name_and_user_id(tag, user.id) <= 1:
                        Tags.delete_tag_by_name_and_user_id(tag, user.id)
                
                # 添加新标签
                for tag in new_tags - old_tags:
                    existing_tag = Tags.get_tag_by_name_and_user_id(tag, user.id)
                    if not existing_tag:
                        Tags.insert_new_tag(tag, user.id)
                
                updated_meta["tags"] = list(new_tags)
            
            chat_record.meta = updated_meta
            chat_record.updated_at = int(time.time())
            
            db.commit()
            db.refresh(chat_record)
            
            return ChatResponse(**ChatModel.model_validate(chat_record).model_dump())
            
    except Exception as e:
        log.error(f"Error updating chat summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat summary"
        )


############################
# GetChatStatistics
############################


@router.get("/statistics", response_model=dict)
async def get_chat_statistics(user=Depends(get_verified_user)):
    """
    获取聊天统计信息，包括所有科目、知识点等数据
    """
    try:
        chats = Chats.get_chats_by_user_id(user.id)
        
        subjects = set()
        knowledge_points = set()
        all_tags = set()
        
        for chat in chats:
            meta = chat.meta or {}
            
            # 收集科目
            if meta.get('subject'):
                subjects.add(meta['subject'])
            
            # 收集知识点
            if meta.get('knowledge_points'):
                knowledge_points.update(meta['knowledge_points'])
            
            # 收集标签
            if meta.get('tags'):
                all_tags.update(meta['tags'])
        
        return {
            "subjects": sorted(list(subjects)),
            "knowledge_points": sorted(list(knowledge_points)),
            "tags": sorted(list(all_tags)),
            "total_chats": len(chats)
        }
        
    except Exception as e:
        log.error(f"Error getting chat statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat statistics"
        )


############################
# SearchChatsByMetadata
############################


@router.post("/search", response_model=list[ChatResponse])
async def search_chats_by_metadata(
    data: dict,  
    user=Depends(get_verified_user)
):
    """
    根据科目、知识点、标签等元数据搜索聊天
    """
    try:
        chats = Chats.get_chats_by_user_id(user.id)
        
        subject_filter = data.get('subject')
        knowledge_points_filter = data.get('knowledge_points', [])
        tags_filter = data.get('tags', [])
        
        filtered_chats = []
        
        for chat in chats:
            meta = chat.meta or {}
            match = True
            
            # 科目过滤
            if subject_filter and meta.get('subject') != subject_filter:
                match = False
                continue
            
            # 知识点过滤 - 至少包含一个指定的知识点
            if knowledge_points_filter:
                chat_knowledge_points = set(meta.get('knowledge_points', []))
                if not any(kp in chat_knowledge_points for kp in knowledge_points_filter):
                    match = False
                    continue
            
            # 标签过滤 - 至少包含一个指定的标签
            if tags_filter:
                chat_tags = set(meta.get('tags', []))
                if not any(tag in chat_tags for tag in tags_filter):
                    match = False
                    continue
            
            if match:
                filtered_chats.append(ChatResponse(**chat.model_dump()))
        
        # 按更新时间排序
        filtered_chats.sort(key=lambda x: x.updated_at, reverse=True)
        
        return filtered_chats
        
    except Exception as e:
        log.error(f"Error searching chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search chats"
        )


############################
# ToggleMistakeById
############################


@router.post("/{id}/mistake", response_model=Optional[ChatResponse])
async def toggle_mistake_by_id(id: str, user=Depends(get_verified_user)):
    """
    切换聊天的错题状态
    """
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )
    
    try:
        with get_db() as db:
            chat_record = db.get(Chat, id)
            
            # 切换错题状态
            updated_meta = {**chat_record.meta}
            is_mistake = updated_meta.get("is_mistake", False)
            updated_meta["is_mistake"] = not is_mistake
            
            chat_record.meta = updated_meta
            chat_record.updated_at = int(time.time())
            
            db.commit()
            db.refresh(chat_record)
            
            return ChatResponse(**ChatModel.model_validate(chat_record).model_dump())
            
    except Exception as e:
        log.error(f"Error toggling mistake status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle mistake status"
        )


############################
# GetMistakeChats
############################


@router.get("/mistakes", response_model=list[ChatResponse])
async def get_mistake_chats(user=Depends(get_verified_user)):
    """
    获取所有错题聊天
    """
    try:
        chats = Chats.get_chats_by_user_id(user.id)
        
        mistake_chats = []
        for chat in chats:
            meta = chat.meta or {}
            if meta.get("is_mistake", False):
                mistake_chats.append(ChatResponse(**chat.model_dump()))
        
        # 按更新时间排序
        mistake_chats.sort(key=lambda x: x.updated_at, reverse=True)
        
        return mistake_chats
        
    except Exception as e:
        log.error(f"Error getting mistake chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get mistake chats"
        )


############################
# GetSubjectStatistics
############################


@router.get("/statistics/subjects", response_model=dict)
async def get_subject_statistics(user=Depends(get_verified_user)):
    """
    获取按科目分类的统计信息
    """
    try:
        chats = Chats.get_chats_by_user_id(user.id)
        
        subject_stats = {}
        mistake_stats = {}
        
        for chat in chats:
            meta = chat.meta or {}
            subject = meta.get('subject', '未分类')
            is_mistake = meta.get('is_mistake', False)
            
            # 总数统计
            if subject not in subject_stats:
                subject_stats[subject] = {
                    'total': 0,
                    'mistakes': 0,
                    'knowledge_points': set()
                }
            
            subject_stats[subject]['total'] += 1
            
            if is_mistake:
                subject_stats[subject]['mistakes'] += 1
            
            # 收集知识点
            if meta.get('knowledge_points'):
                subject_stats[subject]['knowledge_points'].update(meta['knowledge_points'])
        
        # 转换set为list
        for subject in subject_stats:
            subject_stats[subject]['knowledge_points'] = list(subject_stats[subject]['knowledge_points'])
        
        return subject_stats
        
    except Exception as e:
        log.error(f"Error getting subject statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subject statistics"
        )
