import glob
import os

from git import Repo
from llama_index import (
    ServiceContext,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.agent import OpenAIAgent
from llama_index.llms import MockLLM, OpenAI
from llama_index.tools.query_engine import QueryEngineTool

from menderbot.llm import is_test_override

PERSIST_DIR = ".menderbot/ingest"
INDEX_FILE_NAMES = [
    "docstore.json",
    "graph_store.json",
    "index_store.json",
    "vector_store",
]


def delete_index(persist_dir: str) -> None:
    if os.path.exists(persist_dir):
        map(os.remove, glob.glob(os.path.join(persist_dir, "*.json")))


def ingest_repo(replace=False) -> None:
    if replace:
        delete_index(PERSIST_DIR)
    excluded_paths = ["Pipfile.lock"]
    repo = Repo(".")
    commit = repo.commit("HEAD")
    
    file_paths = [
        item.path # type: ignore
        for item in commit.tree.traverse()
        if item.type == "blob" and item.path not in excluded_paths # type: ignore
    ]

    def filename_fn(filename: str) -> dict:
        return {"file_name": filename}

    documents = SimpleDirectoryReader(
        input_files=file_paths,
        recursive=True,
        file_metadata=filename_fn,
    ).load_data()
    index = VectorStoreIndex.from_documents(
        documents,
        show_progress=True,
    )
    index.storage_context.persist(persist_dir=PERSIST_DIR)


def index_exists() -> bool:
    return all(
        [
            os.path.exists(os.path.join(PERSIST_DIR, filename))
            for filename in INDEX_FILE_NAMES
        ]
    )


def load_index():
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    return load_index_from_storage(storage_context)


def get_llm():
    if is_test_override():
        return MockLLM(max_tokens=5)
    return OpenAI(temperature=0, model="gpt-3.5-turbo")


def get_service_context() -> ServiceContext:
    return ServiceContext.from_defaults(llm=get_llm())


def get_query_engine():
    if index_exists():
        return load_index().as_query_engine(
            similarity_top_k=5, service_context=get_service_context()
        )
    return VectorStoreIndex.from_documents([]).as_query_engine(
        service_context=get_service_context()
    )


def ask_index(query: str):
    return get_query_engine().query(query)


def get_chat_engine(verbose=False) -> OpenAIAgent:
    system_prompt = """
You are a Menderbot chat agent discussing a legacy codebase.
"""
    tool_description = """Useful for running a natural language query
about the codebase and get back a natural language response.
"""
    query_engine_tool = QueryEngineTool.from_defaults(
        query_engine=get_query_engine(), description=tool_description
    )
    service_context = get_service_context()
    llm = service_context.llm
    return OpenAIAgent.from_tools(
        tools=[query_engine_tool], llm=llm, verbose=verbose, system_prompt=system_prompt
    )
