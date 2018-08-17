# qlite
SQLite3 wrapper which makes SQLite3 asynchronous in the sense that it can be used in async await code.

# How Does qlite achieve this?
qlite does all sorts of horrible things with threads and callbacks to achieve what looks like async interaction with SQLite3. When run in async program all other async code will be able to continue while you await on your SQLite3 interactions.

# Example Useage
```python3
from qlite import Database

db = Database('play.db')

async def use():
    conn = await db()
    await conn.execute('''CREATE TABLE stocks (date text, trans text, symbol text, qty real, price real)''')
    await conn.commit()
    await conn.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(use())
```
We create a Database instance in one and only one location in our application. We can then get a connection to this Database by calling our created instance. We can then use async calls to our database, with a number of SQLite3 API methods already implemented. Once we are done with our connection we close it, allowing other callers to interact with the database.

## Implemented Async Methods
* Connection.execute()
* Connection.executemany()
* Connection.commit()
* Connection.close()
* Connection.fetchone()
* Connection.fetchmany()

## TODO
* Improve Code Reusue
* Add more methods to API (including aysnc iterators)
* Make an example APP
