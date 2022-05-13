import signal
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter import messagebox,filedialog
from PIL import Image, ImageTk
from functools import partial
import cv2
from igraph import Plot
from max_clique_search import BpmnGraphParser, modular_product_graph, get_max_clique_bk2, color_similarity, get_max_clique_bk1
from tkinter import messagebox


class Application(tk.Frame):
    def __init__(self,master):
        super().__init__(master)
        self.pack()

        self.master.geometry("1280x960")
        self.master.title("BPMN similarity search utility")

        self.image_bgr = dict()
        self.height = dict()
        self.width = dict()
        self.new_size = dict()
        self.image_bgr_resize = dict()
        self.image_rgb = dict()
        self.image_PIL = dict()
        self.image_tk = dict()
        self.filename = dict()
        self.BPMNObject = dict()
        self.GraphObject = dict()
        self.label = dict()
        self.algorithm = get_max_clique_bk1
        self.create_widgets()

    def create_widgets(self):
        #Canvases
        self.canvas1 = tk.Canvas(self)
        self.canvas1.configure(width=640, height=480, bg='orange')
        self.canvas1.grid(column=1, row=0)

        self.canvas2 = tk.Canvas(self)
        self.canvas2.configure(width=640, height=480, bg='orange')
        self.canvas2.grid(column=2, row=0)

        self.label[self.canvas1] = Label(self)
        self.label[self.canvas1].grid(column=1, row=1)
        self.label[self.canvas2] = Label(self)
        self.label[self.canvas2].grid(column=2, row=1)
        #Frame
        self.frame_button = ttk.LabelFrame(self)
        self.frame_button.configure()
        self.frame_button.grid(column=1,row=1)
        self.frame_button.grid(padx=20, pady=20, columnspan=2)

        #load 1 Button
        self.button_open_bpmn_one = ttk.Button(self.frame_button)
        self.button_open_bpmn_one.configure(text = 'Load input 1.')
        self.button_open_bpmn_one.grid(column=0, row=1)
        self.button_open_bpmn_one.configure(command=partial(self.loadBPMN,self.canvas1))

        # Clear Button
        self.start = ttk.Button( self.frame_button )
        self.start.configure( text='Start search' )
        self.start.grid(column=1, row=1 )
        self.start.configure(command=self.startSearch)

        # load2 Button
        self.button_open_bpmn_two = ttk.Button( self.frame_button )
        self.button_open_bpmn_two.config( text='Load input 2.' )
        self.button_open_bpmn_two.grid(column=2, row=1 )
        self.button_open_bpmn_two.configure(command=partial(self.loadBPMN,self.canvas2))

        # Clear Button
        self.clear = ttk.Button( self.frame_button )
        self.clear.configure( text='Clear inputs' )
        self.clear.grid(column=0, row=2, columnspan=4)
        self.clear.configure(command=self.clearInputs)


        #toggle button
        self.toggle_button = ttk.Button(self.frame_button, text="Bron-Kerbosch simple mode")
        self.toggle_button.grid(column=0, row=3, columnspan=4)
        self.toggle_button.configure(command=self.toggleCallback)

    def toggleCallback(self):
        if self.toggle_button.config('text')[-1] == 'Bron-Kerbosch simple mode':
            self.toggle_button.config(text='Bron-Kerbosch with pivot')
            self.algorithm = get_max_clique_bk2
        else:
            self.toggle_button.config(text='Bron-Kerbosch simple mode')
            self.algorithm = get_max_clique_bk1

    # Event Call Back
    def loadBPMN(self, canvas):
        self.filename[canvas] = filedialog.askopenfilename()
        self.label[canvas]['text'] = str(self.filename[canvas]).split('/')[-1]
        self.label[canvas]['bg'] = "yellow"
        self.BPMNObject[canvas] = BpmnGraphParser(self.filename[canvas])
        self.GraphObject[canvas] = self.BPMNObject[canvas].get_graph()
        plot = Plot("tmp.png", background="white")
        plot.add(self.GraphObject[canvas], margin = 100)
        plot.save()
        self.loadImage(canvas)

    # Event Call Back
    def loadImage(self, canvas):
        self.image_bgr[canvas] = cv2.imread("tmp.png")
        self.height[canvas], self.width[canvas] = self.image_bgr[canvas].shape[:2]
        
        if self.width[canvas] > self.height[canvas]:
            self.new_size[canvas] = (1280,960)
        else:
            self.new_size[canvas] = (640,480)

        self.image_bgr_resize[canvas] = cv2.resize(self.image_bgr[canvas], self.new_size[canvas], interpolation=cv2.INTER_AREA)
        self.image_rgb[canvas] = cv2.cvtColor( self.image_bgr_resize[canvas], cv2.COLOR_BGR2RGB )

        self.image_PIL[canvas] = Image.fromarray(self.image_rgb[canvas]) 
        self.image_tk[canvas] = ImageTk.PhotoImage(self.image_PIL[canvas])
        canvas.create_image(320, 240, image=self.image_tk[canvas])

    def clearInputs(self):
        self.canvas1.delete("all")
        self.canvas2.delete("all")
        self.image_bgr = dict()
        self.height = dict()
        self.width = dict()
        self.new_size = dict()
        self.image_bgr_resize = dict()
        self.image_rgb = dict()
        self.image_PIL = dict()
        self.image_tk = dict()
        self.filename = dict()
        self.BPMNObject = dict()
        self.GraphObject = dict()
        self.label[self.canvas1]['text'] = ""
        self.label[self.canvas2]['text'] = ""

    def startSearch(self):
        if len(self.GraphObject) < 2:
            messagebox.showwarning("Warning", "Please load in the BPMN XMLs!")
            return
        self.start['state'] = DISABLED
        G, H = self.GraphObject.values()
        MODULAR_PRODUCT_GRAPH = modular_product_graph(G, H)
        # signal.alarm(10)
        max_clique = self.algorithm(MODULAR_PRODUCT_GRAPH)
        # signal.alarm(0)
        if max_clique:
            common_edge_count = color_similarity(MODULAR_PRODUCT_GRAPH, max_clique, G, H)
            print(f"Talált maximimum klikk élszáma: {common_edge_count}")

            for canvas in self.GraphObject:
                plot = Plot("tmp.png", background="white")
                plot.add(self.GraphObject[canvas], margin = 100)
                plot.save()
                self.loadImage(canvas)
        self.start['state'] = NORMAL

    def quit_app(self):
        self.Msgbox = tk.messagebox.askquestion("Exit Applictaion", "Are you sure?", icon="warning")
        if self.Msgbox == "yes":
            self.master.destroy()
        else:
            tk.messagebox.showinfo("Return", "you will now return to application screen")

def main():
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()

if __name__ == "__main__":
    main()
