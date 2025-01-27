from abc import abstractmethod
from typing import List

from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from selenium.webdriver.remote.webelement import WebElement

from src.data_objects.job_posting import JobPosting
from src.utils.web_scrapping.hcm.hcm_crawler import HcmCrawler


class VectorStoreHcmCrawler(HcmCrawler):
    '''
    Abstract HCM Crawler class that uses vector_
    '''
    def __init__(self, driver, posting: JobPosting):
        super.__init__(driver, posting)
        self.current_page_vector_store = None
        self.embeddings = OpenAIEmbeddings()
        pass

    def __break_page_into_vector_store(self):
        try:
            # Get the page source
            page_source = self.driver.page_source

            # Initialize a text splitter to break HTML into smaller chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,  # Size of each chunk
                chunk_overlap=200,  # Overlap between chunks
                separators=["\n", " "]
            )

            # Split the page source into chunks
            html_chunks = text_splitter.split_text(page_source)

            embeddings = OpenAIEmbeddings()

            # Create a FAISS vector store
            vector_store = FAISS.from_texts(html_chunks, embeddings)

            # Define the query: "a button or link to login"
            query = "a button or link to login"

            # Use the vector store to find the most relevant chunk
            retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
            qa_chain = RetrievalQA.from_chain_type(
                llm=OpenAI(),
                retriever=retriever,
                return_source_documents=True
            )
            # Run the query
            result = qa_chain.run(query)

    @abstractmethod
    def _requires_login(self):
        '''
        protected method  that will check the state of the web driver to see if the loaded page has a "log in element"
        :returns true if this page requires a login, false if we can apply without loggin in
        '''
        pass

    @abstractmethod
    def _attempt_login(self):
        '''
        protected method that will attempt to login with the current state of the web driver using the
        default_account_email and default_account_password defined in the secrets.yaml and stored in the global_config
        object

        :return: true if we were able to log in, false or an exception if there was an error
        '''
        pass

    @abstractmethod
    def _create_account(self):
        '''
        protected method that will attempt to create an account with the current state of the web driver using the
        default_account_email and default_account_password defined in the secrets.yaml and stored in the global_config
        object

        :return: true if we were able to create an account, false or an exception if there was an error
        '''
        pass

    @abstractmethod
    def _get_application_elements(self) -> List[WebElement]:
        '''
        protected method that will use AI to find all elements on the page that need to be filled out as part of the
        application.

        NOTE: there are 2 implemenations of doing this, 1 using vector storage to find what elements on the page
        are required inputs, and the other using just a LLM directly to fill out all html elements that need to be
        filled out.
        :return: a list of all webElements that need to be filled out, WITH their appropriate FILLED IN DATA
        '''
        pass

    @abstractmethod
    def _fill_application_elements(self, web_elements: List[WebElement]):
        '''
        protected method that will fill out all elements required for the applicaiton to move its state forward.
        - If we are using LLM's these web elements will be filled out and will simply need to be applied to the driver
        - If we are using vectorstore we will need to pull the most relevant data
        It will progress the webdriver states by submitting all of these elements too
        :param webElements: elements that need to be filled out for the application
        '''
        pass

    @abstractmethod
    def _attempt_submit_app(self):
        '''
        Attempts to submit the application and confirm that the application is fully completed.
        :return: true if the application was able to be submitted
        '''
        pass