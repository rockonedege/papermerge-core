from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from django.db.utils import IntegrityError

from papermerge.core.models import User, Document
from papermerge.core.schemas.nodes import Node as PyNode
from papermerge.core.schemas.nodes import UpdateNode as PyUpdateNode
from papermerge.core.schemas.folders import Folder as PyFolder
from papermerge.core.schemas.folders import CreateFolder as PyCreateFolder
from papermerge.core.schemas.documents import CreateDocument as PyCreateDocument
from papermerge.core.schemas.documents import Document as PyDocument
from papermerge.core.models import BaseTreeNode, Folder

from .auth import oauth2_scheme
from .auth import get_current_user as current_user
from .params import CommonQueryParams
from .paginator import PaginatorGeneric, paginate


router = APIRouter(
    prefix="/nodes",
    tags=["nodes"],
    dependencies=[Depends(oauth2_scheme)]
)


@router.get("/")
def get_nodes(user: User = Depends(current_user)) -> RedirectResponse:
    """Redirects to current user home folder"""
    parent_id = str(user.home_folder.id)
    return RedirectResponse(
        f"/nodes/{parent_id}"
    )


@router.get("/{parent_id}", response_model=PaginatorGeneric[PyNode])
@paginate
def get_node(
    parent_id,
    params: CommonQueryParams = Depends(),
    user: User = Depends(current_user)
):
    """Returns a list nodes with given parent_id of the current user"""
    order_by = ['ctype', 'title']

    if params.order_by:
        order_by = [
            item.strip() for item in params.order_by.split(',')
        ]

    return BaseTreeNode.objects.filter(
        parent_id=parent_id,
        user_id=user.id
    ).order_by(*order_by)


@router.post("/")
def create_node(
    pynode: PyCreateFolder | PyCreateDocument,
    user: User = Depends(current_user)
) -> PyFolder | PyDocument:

    try:
        if pynode.ctype == "folder":
            node = Folder.objects.create(
                title=pynode.title,
                user_id=user.id,
                parent_id=pynode.parent_id
            )
            klass = PyFolder
        else:
            # if user does not specify document's language, get that
            # value from user preferences
            if pynode.lang is None:
                pynode.lang = user.preferences['ocr__language']

            node = Document.objects.create_document(
                title=pynode.title,
                lang=pynode.lang,
                user_id=user.id,
                parent_id=pynode.parent_id,
                size=0,
                page_count=0,
                file_name=pynode.title
            )
            klass = PyDocument
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Title already exists"
        )

    return klass.from_orm(node)


@router.patch("/{node_id}")
def update_node(
    node_id: UUID,
    node: PyUpdateNode,
    user: User = Depends(current_user)
) -> PyNode:
    """Updates node

    parent_id is optional field. However, when present, parent_id
    should be non empty string (UUID).
    """
    try:
        old_node = BaseTreeNode.objects.get(id=node_id, user_id=user.id)
    except BaseTreeNode.DoesNotExist:
        raise HTTPException(
            status_code=404,
            detail="Does not exist"
        )

    for key, value in node.dict().items():
        if value is not None:
            setattr(old_node, key, value)
    old_node.save()

    return PyNode.from_orm(old_node)


@router.delete("/")
def delete_nodes(
    list_of_uuids: List[UUID],
    user: User = Depends(current_user)
) -> List[UUID]:
    """Deletes nodes with specified UUIDs

    Returns a list of UUIDs of actually deleted nodes.
    In case nothing was deleted (e.g. no nodes with specified UUIDs
    were found) - will return an empty list.
    """
    deleted_nodes_uuids = []
    for node in BaseTreeNode.objects.filter(
        user_id=user.id, id__in=list_of_uuids
    ):
        deleted_nodes_uuids.append(
            node.id
        )
        node.delete()

    return deleted_nodes_uuids
