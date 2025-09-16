import webbrowser 

from flask import Flask, render_template
from threading import Timer

#User input
name_example = 'hellosepolia.eth'
name = input("ENS name [empty for hellosepolia.eth example]: ")
if name == "":
    name = name_example

#Start flask server with dApp
print("starting dApp")
app = Flask(__name__, static_url_path='',
                  static_folder=f"retrieved/{name}/latest",
                  template_folder=f"retrieved/{name}/latest") 

@app.route("/")
def hello():
    return render_template("index.html")

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(host="127.0.0.1", port="")