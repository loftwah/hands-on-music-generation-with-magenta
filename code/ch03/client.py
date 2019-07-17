from multiprocessing import Process, Pipe

def f(child_conn):
    p = Process(target=f, args=(child_conn,))
    p.start()
    msg = "Hello"
    child_conn.send(msg)
    child_conn.close()
