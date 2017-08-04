# -*- coding: utf-8 -*-
"""This script takes two timepoints t0, t1 and a time step.
   For each timepoint t between t0 and t1 in steps of the given time step,
   it then displays markers at the locations
   of all vehicle journeys in the network at time point t. The attributes
   that are displayed for each vehjourney can be configured by changing function
   addVehJourneyMarker. The script inserts count locations as markers, so these network
   objects should not be used for other purposes in the network.
   Screenshots of the displays are saved to JPG files. The script prompts the
   user for a base file name and appends the time (in seconds) to it.

   Requirements:
   1) Visum model must contain a PuT timetable.
   2) For best results load the graphics parameters vehjourneylocations.gpa. Load
      selectively the settings for count locations and make that layer visible.
   3) Requires the VisumPy library.
   4) To create a movie sequence out of the screenshots you require a tool such as MakeAVI.
      This tool is open source and can be downloaded for free at http://makeavi.sourceforge.net/."""
import os
import sys
from VisumPy.helpers import GetMulti, secs2HHMMSS, HHMMSS2secs
from VisumPy.Tk import *
from datetime import datetime
import tkFileDialog


class Window:
    def __init__(self):
        self.root = Tk.Tk()
        Tk.Label(self.root, text="Please specify the following options for the MaaS animations.").pack()
        Tk.Label(self.root, text="").pack()

        frame = Tk.Frame(self.root)
        frame.pack()
        Tk.Label(frame, text="Time step for jpeg generation:", relief=Tk.SUNKEN).grid(row=0, column=1)
        self.e1 = Tk.Entry(frame, relief=Tk.SUNKEN, justify=Tk.CENTER)
        self.e1.insert(0, "5")
        self.e1.grid(row=0, column=2)
        Tk.Label(frame, text="seconds.", relief=Tk.SUNKEN).grid(row=0, column=3)
        Tk.Label(frame, text=" ").grid(row=1)

        Tk.Label(frame, text="Starttime (hour:min:sec):", relief=Tk.SUNKEN).grid(row=3, column=0, sticky=Tk.W+Tk.E)
        self.entry_st = range(3)
        for i, t in zip(range(3), ["06", "00", "00"]):
            self.entry_st[i] = Tk.Entry(frame, justify=Tk.CENTER, relief=Tk.SUNKEN)
            self.entry_st[i].insert(0, t)
            self.entry_st[i].grid(row=3, column=1+i, sticky=Tk.W+Tk.E)

        Tk.Label(frame, text="Endtime (hour:min:sec):", relief=Tk.SUNKEN).grid(row=4, column=0, sticky=Tk.W+Tk.E)
        self.entry_et = range(3)
        for i, t in zip(range(3), ["08", "00", "01"]):
            self.entry_et[i] = Tk.Entry(frame, justify=Tk.CENTER, relief=Tk.SUNKEN)
            self.entry_et[i].insert(0, t)
            self.entry_et[i].grid(row=4, column=1+i, sticky=Tk.W+Tk.E)
        Tk.Label()

        # OK-Button:
        Tk.Label(self.root, text="").pack()
        Tk.Button(self.root, text="OK", command=self.ok).pack()

        self.root.mainloop()

    def ok(self):
        self.starttime = datetime(2017, 1, 1, int(self.entry_st[0].get()),
                                  int(self.entry_st[1].get()), int(self.entry_st[2].get()))
        self.endtime = datetime(2017, 1, 1, int(self.entry_et[0].get()),
                                int(self.entry_et[1].get()), int(self.entry_et[2].get()))
        self.timestep = int(self.e1.get())
        self.root.destroy()


def sectoclock(t):

    if t > 3600*24:
        t = t % (3600*24)

    return secs2HHMMSS(t)


def sectoclock2(t):

    if t > 3600*24:
        t = t % (3600*24)

    t = secs2HHMMSS(t).replace(":", "")

    return t


def isOnNode(lri):
    try:
        nodeno = lri.AttValue("NODENO")  # war "NODE\\NO", müsste immer gleich sein [JS]
        return nodeno > 0  # ergibt stets true, wenn etwas in nodeno drinsteht
    except:
        return False


def getVehJourneyPos(vehjourney, time):
    """ returns the location of the vehjourney at a given time
        as an offset along a link, if the time is within the running
        time of the vehjourney.
    vehjourney - object - a vehicle journey
    time - integer - current time in seconds from midnight """

    vjarr = vehjourney.AttValue("ARR")
    vjdep = vehjourney.AttValue("DEP")
    if time < vjdep or time > vjarr:
        # the vehjourney does not run at the given time --> location undefined
        return None, None, None, None

    # find location in the line route item sequence
    vjitems = vehjourney.VehicleJourneyItems
    vjiarr = GetMulti(vjitems, "ARR")
    vjidep = GetMulti(vjitems, "DEP")
    vjiidx = GetMulti(vjitems, "TIMEPROFILEITEM\\LINEROUTEITEM\\INDEX")
    
    # ------- Hier gewünschtes Attribut einfügen, welches für die Klassifizierte Darstellung der Zählstellen verwendet wird -----------
    vjishvol = GetMulti(vjitems, "VOL(AP)") # von SHVOL geändert [JS]

    # Get attribute SHVOL for
    shvol = None

    # check whether vehjourney is stopping somewhere
    found = False
    for i in xrange(1, len(vjitems.GetAll)-1):  # all except first and last item
        if vjiarr[i] <= time <= vjidep[i]:
            fromidx = vjiidx[i]
            shvol   = vjishvol[i]
            toidx   = vjiidx[i+1]
            offset  = 0.0
            found   = True
            break

    # if not found, vehjourney must be between stops. Where?
    if not found:
        for i in xrange(len(vjitems.GetAll)-1):
            if vjidep[i] <= time <= vjiarr[i+1]:
                fromidx = vjiidx[i]
                shvol   = vjishvol[i]
                toidx   = vjiidx[i+1]
                if vjiarr[i+1] - vjidep[i] > 0:
                    offset = (time-vjidep[i]) / (vjiarr[i+1] - vjidep[i])
                else:
                    offset = 0
                found = True
                break

    if not found:
        # no vehicle journey items found
        return None, None, None, None

    # Now we know that the vehicle is between line route items with index fromidx and toidx
    # and the 0..1 fraction of its location along the way is stored in offset.
    # Find the link corresponding to the offset:
    lritems = vehjourney.LineRoute.LineRouteItems.GetAll
    nodenos = []
    lengths = []
    fromidx = int(fromidx)
    toidx   = int(toidx)
    # CAUTION: in the zero-based Python array the first item is at position fromidx-1,
    # the last item is at toidx-1!!
    # first item can be on node or link
    if isOnNode(lritems[fromidx-1]):
        nodeno = lritems[fromidx-1].AttValue("NODENO")
        nodenos.append(nodeno)
        lengths.append(lritems[fromidx-1].AttValue("OUTLINK\\LENGTH"))
    else:
        nodeno = lritems[fromidx-1].AttValue("OUTLINK\\FROMNODENO")
        nodenos.append(nodeno)
        lengths.append(lritems[fromidx-1].AttValue("OUTLINK\\LENGTH") * (1-lritems[fromidx-1].AttValue("STOPPOINT\\RELPOS")))
    # ignore intermediate stoppoints on links
    for i in xrange(fromidx, toidx-1):
        if isOnNode(lritems[i]):
            nodeno = lritems[i].AttValue("NODENO")
            nodenos.append(nodeno)
            lengths.append(lritems[i].AttValue("OUTLINK\\LENGTH"))
    # last item can be on node or link
    if isOnNode(lritems[toidx-1]):
        nodeno = lritems[toidx-1].AttValue("NODENO")
        nodenos.append(nodeno)
    else:
        # correct last link length (only up to stoppoint location)
        lengths[-1] = (lritems[toidx-1].AttValue("INLINK\\LENGTH") * lritems[toidx-1].AttValue("STOPPOINT\\RELPOS"))
        nodenos.append(lritems[toidx-1].AttValue("INLINK\\TONODENO"))

    if not (len(nodenos) == len(lengths) + 1):
        return None, None, None, None

    # cumulate length along line route until we reach the vehjourney location
    location = offset * sum(lengths)
    cumlength = 0.0
    i = 0
    while cumlength + lengths[i] < location:
        cumlength += lengths[i]
        i += 1

    # it must be in the last link we considered, find relpos within that link
    link = Visum.Net.Links.ItemByKey(nodenos[i], nodenos[i+1])
    if link.AttValue("LENGTH") > 0:
        relpos = (location - cumlength) / link.AttValue("LENGTH")
    else:
        relpos = 0

    return (Visum.Net.Nodes.ItemByKey(nodenos[i]),
            Visum.Net.Nodes.ItemByKey(nodenos[i+1]),
            relpos, shvol)


def addVehJourneyMarker(vehjourney, fromnode, tonode, relpos, shvol):
    """inserts a count location at the location specified and copies over selected
       attributes of the vehicle journey. Modify this to include whichever attributes
       you want."""
    # cloc = Visum.Net.AddCountLocation(vehjourney.AttValue("NO"), fromnode, tonode)

    # # correct rounding errors
    # if(relpos < 0):
        # relpos = 0
    # if(relpos > 1):
        # relpos = 1

    # cloc.SetAttValue("RELPOS", relpos)
    # cloc.SetAttValue("CODE", vehjourney.AttValue("LINENAME"))
    # cloc.SetAttValue("NAME", secs2HHMMSS(vehjourney.AttValue("DEP")))

    # number, fromnodeno, tonodeno, linkno wurden als float ausgegeben --> int(...)
    number    =    int(vehjourney.AttValue("NO"))
    code    =    vehjourney.AttValue("NAME_TEMP")
    name    =    secs2HHMMSS(vehjourney.AttValue("DEP"))
    fromnodeno    =    int(fromnode.AttValue("NO"))
    tonodeno    =    int(tonode.AttValue("NO"))
    linkno    =     int(Visum.Net.Links.ItemByKey(fromnodeno,tonodeno).AttValue("NO"))
    # if shvol==None:                                                
         # shvol=Visum.Net.VehicleJourneyItems.AttValue("VOL(AP)")

    tmp_string = str(number)+";"+str(code)+";"+str(name)+";"+str(linkno)+";"+str(fromnodeno)+";"+str(tonodeno)+";"+str(relpos)+";"+str(shvol)

    return tmp_string


def displayAllVehJourneys(time, allvj):
    """for each vehicle journey which is on its way at the given time, insert a marker
    at the location at that time."""

    netfile = Visum.GetPath(1) + "add_vehicles.net"
    with open(netfile, "w") as fo:
        # Write net file to add vehicles as countlocations:
        fo.write(u"$VISION\n$VERSION:VERSNR;FILETYPE;LANGUAGE;UNIT\n10;Net;ENG;KM\n$COUNTLOCATION:NO;CODE;NAME;LINKNO;FROMNODENO;TONODENO;RELPOS;number_of_passengers\n")

        for i, vj in enumerate(allvj):
            fromnode, tonode, relpos, shvol = getVehJourneyPos(vj, time)

            if fromnode is not None:
                tmp_string = addVehJourneyMarker(vj, fromnode, tonode, relpos, shvol)
                fo.write(tmp_string+"\n")

    Visum.LoadNet(netfile,True)
    os.remove(netfile)


def clearVehJourneyMarkers():
    # allcloc = Visum.Net.CountLocations.GetAll
    # for cloc in allcloc:
        # Visum.Net.RemoveCountLocation(cloc)
    Visum.Net.CountLocations.RemoveAll()

# Main program
# prompt user for time and display vehjourneys


def main():

    # Ask and load the pfd file:
    messageBox("Please choose the path of the Project File Directory (.pfd) of your project." +
               "Please be sure that all paths are set correctly to the current project folder.")

    root = Tk.Tk()
    pfdfile = tkFileDialog.askopenfile(initialdir="D:\Animate_Vehicles\Projektverzeichnis", parent=root,
                                       title="Select Project File Directory", defaultextension=".pfd",
                                       filetypes=(("all files", "*.*"), ("pfd files", "*.pfd")))
    pfdfile = pfdfile.name
    root.destroy()

    Visum.LoadPathFile(pfdfile)

    # Add user-defined attribute "number_of_passengers":
    # muss zu gpa-Einstellungen bei Zählstellen passen; bzw. andersrum
    '''
    try:
        Visum.Net.CountLocations.AddUserDefinedAttribute("number_of_passengers","number_of_passengers","number_of_passengers", 240) # funktioniert nicht
    except:
        pass
    '''
    # count_loc_uda = "number_of_passengers"
    # Visum.Net.CountLocations.AddUserDefinedAttribute(count_loc_uda,count_loc_uda,count_loc_uda,2,2)
    
    # hinzugefügt [JS]
    # Visum.Net.GraphicParameters.Open("D02_Zoom_Linienwege_mit_Legende.gpa")
    # Visum.Net.GraphicParameters.OpenXML("AnimVeh_mBeschr_Quadr.gpax")
    
    # Add node for drawing time:
    xmin, ymin, xmax, ymax = Visum.Graphic.GetWindow()
    nodenomax = int(max(GetMulti(Visum.Net.Nodes, "No")))+1
    Visum.Net.AddNode(nodenomax)  # setzt Umlegung zwangsläufig zurück
    Visum.Net.Nodes.ItemByKey(nodenomax).SetAttValue("Name", "Time")
    Visum.Net.Nodes.ItemByKey(nodenomax).SetAttValue("xcoord", xmin + 0.08*(xmax-xmin))  # war 0.1
    Visum.Net.Nodes.ItemByKey(nodenomax).SetAttValue("ycoord", ymin + 0.95*(ymax-ymin))  # war 0.93

    # hinzugefügt [JS]
    # Visum.Procedures.Open(Visum.GetPath(12)+"D02_V05_UmlegungOEV_Kapazitaetsbeschraenkung.par")
    # Visum.Procedures.Execute()
    # Legenden-Parameter lesen, wie? --> in .gpa oben integriert [JS]
    
    NodeFilter = Visum.Filters.NodeFilter()
    NodeFilter.UseFilter = True
    NodeFilter.Init()
    NodeFilter.AddCondition("OP_NONE", False, "NO","EqualVal", nodenomax)
    
    # auskommentiert [JS]
    ''' 
    #Set filter to "AV" countlocations: 
    CountLocationFilter = Visum.Filters.CountLocationFilter()
    CountLocationFilter.Init()
    CountLocationFilter.UseFilter = True
    CountLocationFilter.AddCondition("OP_NONE", False, "Code","EqualVal","AV")
    '''

    # Ask for time interval:
    a = Window()
    t0 = a.starttime.strftime("%H:%M:%S")
    t1 = a.endtime.strftime("%H:%M:%S")
    timestep = a.timestep
    print(t0)
    print(t1)

    # Original code:
    t0 = HHMMSS2secs(t0)
    t1 = HHMMSS2secs(t1)
    step = int(timestep)

    basePath = r".\neu"
    basefilename = "DB_API_.jpg"
    basefilename, ext = os.path.splitext(basefilename)
    graphicsPath = Visum.GetPath(33)

    if os.path.abspath(basePath):
        basePath = os.path.join(graphicsPath, basePath)

    allvj = Visum.Net.VehicleJourneys.GetAllActive
    pb = ProgressDlg("Creating images")
    pb.attributes("-topmost", True)
    n_tot = len(range(t0, t1, step))
    icount = 1

    for i, t in enumerate(xrange(t0, t1, step)):
        pb.setMessage("Write jpg: ", icount, n_tot)
        icount += 1
        Visum.Net.Nodes.ItemByKey(nodenomax).SetAttValue("Name", sectoclock(t))
        clearVehJourneyMarkers()
        displayAllVehJourneys(t, allvj)
        try:
            fileName = "%s%s%s" % (basefilename, sectoclock2(t), ext)
            filePath = os.path.join(Visum.GetPath(33) + "neu", fileName)
            Visum.Graphic.Screenshot(filePath)
        except:
            break
        Visum.Graphic.WaitForIdle()
    
    try:
        pb.close()
    except:
        pass

    # eingefügt [JS]
    Visum.Net.CountLocations.RemoveAll() 
    # Visum.Net.CountLocations.DeleteUserDefinedAttribute(count_loc_uda)
    # Remove node for drawing time:
    Visum.Net.RemoveNode(Visum.Net.Nodes.ItemByKey(nodenomax))

main()
