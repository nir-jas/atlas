from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from atlas_api.core.dependencies import get_document_service
from atlas_api.schemas.documents import DocumentResponse, DocumentUploadRequest
from atlas_api.services.documents import DocumentService

router = APIRouter(tags=["documents"])
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
DocumentUploadRequestDep = Annotated[DocumentUploadRequest, Depends(DocumentUploadRequest.as_form)]
UploadFileDep = Annotated[UploadFile, File(...)]


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    payload: DocumentUploadRequestDep,
    service: DocumentServiceDep,
    file: UploadFileDep,
) -> DocumentResponse:
    content = await file.read()
    document = service.upload_document(
        payload=payload,
        original_filename=file.filename,
        content=content,
    )
    return DocumentResponse.model_validate(document)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(service: DocumentServiceDep) -> list[DocumentResponse]:
    return [DocumentResponse.model_validate(document) for document in service.list_documents()]
