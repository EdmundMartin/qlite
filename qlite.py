import asyncio
from asyncio.queues import Queue, QueueEmpty
from concurrent.futures import ThreadPoolExecutor
import sqlite3


class NoActiveCursor(Exception):
    pass


class Database:

    def __init__(self, database, loop=None):
        self.database = database
        self.loop = loop if loop else asyncio.get_event_loop()
        self.connection_semaphore = Queue(maxsize=1)
        self.connection_semaphore.put_nowait({})
        self.__connect_ref = None

    async def __acquire_connection(self):
        await self.connection_semaphore.get()
        return sqlite3.connect(self.database, check_same_thread=False)

    async def __call__(self, *args, **kwargs):
        db = await self.__acquire_connection()
        return Connection(db, self)

    async def __aenter__(self):
        db = await self.__acquire_connection()
        conn = Connection(db, self)
        self.__connect_ref = conn
        return conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.__connect_ref:
            await self.__connect_ref.close()


class Connection:

    def __init__(self, cursor, conn: Database):
        self._cursor = cursor
        self._public_cursor = None
        self._connection = conn
        self._thread = ThreadPoolExecutor(max_workers=1)
        self._result_queue = Queue(maxsize=1)

    def _callback(self, result):
        res = result.result()
        self._result_queue.put_nowait(res)

    async def __get_result(self):
        while True:
            try:
                result = self._result_queue.get_nowait()
            except QueueEmpty:
                await asyncio.sleep(0.0001)
            except Exception as e:
                raise e
            else:
                return result

    def _execute(self, sql: str, parameters=None):
        if not parameters:
            parameters = []
        try:
            result = self._cursor.execute(sql, parameters)
            self._public_cursor = result
            return self
        except Exception as e:
            return e

    async def execute(self, sql, parameters=None):
        task = self._thread.submit(self._execute, sql, parameters=parameters)
        task.add_done_callback(self._callback)
        result = await self.__get_result()
        if isinstance(result, Exception):
            raise result
        return result

    def _execute_many(self, sql, parameters):
        try:
            result = self._cursor.executemany(sql, parameters)
            self._public_cursor = result
            return self
        except Exception as e:
            return e

    async def executemany(self, sql, parameters):
        task = self._thread.submit(self._execute_many, sql, parameters=parameters)
        task.add_done_callback(self._callback)
        result = await self.__get_result()
        if isinstance(result, Exception):
            raise result
        return result

    def _fetch_one(self):
        try:
            result = self._public_cursor.fetchone()
            return result
        except Exception as e:
            return e

    async def fetchone(self):
        if self._public_cursor is None:
            raise NoActiveCursor
        task = self._thread.submit(self._fetch_one)
        task.add_done_callback(self._callback)
        result = await self.__get_result()
        if isinstance(result, Exception):
            raise result
        return result

    def _fetch_all(self):
        try:
            result = self._public_cursor.fetchall()
            return result
        except Exception as e:
            return e

    async def fetchall(self):
        if self._public_cursor is None:
            raise NoActiveCursor
        task = self._thread.submit(self._fetch_all)
        task.add_done_callback(self._callback)
        result = await self.__get_result()
        if isinstance(result, Exception):
            raise result
        return result

    def _commit(self):
        try:
            self._cursor.commit()
            return None
        except Exception as e:
            return e

    async def commit(self):
        task = self._thread.submit(self._commit)
        task.add_done_callback(self._callback)
        result = await self.__get_result()
        if isinstance(result, Exception):
            raise result
        return result

    async def close(self):
        self._cursor.close()
        await self._connection.connection_semaphore.put({})
        return


