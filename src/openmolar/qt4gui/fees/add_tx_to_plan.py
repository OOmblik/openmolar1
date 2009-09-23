# -*- coding: utf-8 -*-
# Copyright (c) 2009 Neil Wallace. All rights reserved.
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# See the GNU General Public License for more details.

'''
provides code to add Xrays, perio items......etc
to the treatment plan
'''

from __future__ import division

import re
from PyQt4 import QtGui

from openmolar.settings import localsettings, fee_keys
from openmolar.qt4gui.dialogs import Ui_customTreatment, addTreat
#-- fee modules which interact with the gui
from openmolar.qt4gui.fees import course_module, fees_module

def offerTreatmentItems(parent, arg):
    '''
    offers treatment items passed by argument
    '''
    Dialog = QtGui.QDialog(parent)
    dl = addTreat.treatment(Dialog, arg, parent.pt)
    result =  dl.getInput()
    return result

def xrayAdd(parent):
    '''
    add xray items
    '''
    if not course_module.newCourseNeeded(parent):
        mylist = ((0, "S"), (0, "M"), (0, "P"))
        chosenTreatments = offerTreatmentItems(parent, mylist)
        for treat in chosenTreatments:
            #(usercode,itemcode,description, fee,ptfee)
            print "treat =", treat
            usercode = treat[0]
            parent.pt.xraypl += usercode + " "
            parent.pt.addToEstimate(1, treat[1], treat[2], 
            treat[3], treat[4], parent.pt.dnt1, 
            parent.pt.cset, "xray %s"% usercode)
        parent.load_treatTrees()
        parent.load_newEstPage()

def perioAdd(parent):
    '''
    add perio items
    '''
    if not course_module.newCourseNeeded(parent):
        mylist = ((0, "SP"), (0, "SP+"))
        chosenTreatments = offerTreatmentItems(parent, mylist)
        for treat in chosenTreatments:
            usercode = treat[1]
            parent.pt.periopl += usercode + " "
            parent.pt.addToEstimate(1,treat[1], treat[2], treat[3],
            treat[4], parent.pt.dnt1, parent.pt.cset, "perio %s"% usercode)
        parent.load_treatTrees()
        parent.load_newEstPage()

def otherAdd(parent):
    '''
    add 'other' items
    '''
    if not course_module.newCourseNeeded(parent):
        mylist = ()
        items = localsettings.treatmentCodes.keys()
        for item in items:
            code = localsettings.treatmentCodes[item]
            if 3500 < int(code) < 4002:
                mylist += ((0, item, code), )
        chosenTreatments = offerTreatmentItems(parent, mylist)
        for treat in chosenTreatments:
            parent.pt.otherpl += "%s "% treat[1]
            parent.pt.addToEstimate(1,treat[1], treat[2], treat[3],
            treat[4], parent.pt.dnt1, parent.pt.cset, "other OT")
        parent.load_newEstPage()
        parent.load_treatTrees()

def customAdd(parent):
    '''
    add 'custom' items
    '''
    if not course_module.newCourseNeeded(parent):
        Dialog = QtGui.QDialog(parent)
        dl = Ui_customTreatment.Ui_Dialog()
        dl.setupUi(Dialog)
        if Dialog.exec_():
            no = dl.number_spinBox.value()
            descr = str(dl.description_lineEdit.text())
            if descr == "":
                descr = "??"
            type = "%s%s"% (no, descr.replace(" ", "_"))
            if len(type) > 5:
                #-- necessary because the est table type col is char(12)
                type = type[:5]
            fee = int(dl.fee_doubleSpinBox.value() * 100)
            ptfee = int(dl.ptFee_doubleSpinBox.value() * 100)

            parent.pt.custompl += "%s "% type
            parent.pt.addToEstimate(no, "4002", descr, fee,
            ptfee, parent.pt.dnt1, "P", "custom %s"% type)
            parent.load_newEstPage()
            parent.load_treatTrees()

def chartAdd(parent, tooth, properties):
    '''
    add treatment to a tooth
    '''
    #-- important stuff. user has added treatment to a tooth
    #-- let's cite this eample to show how this funtion works
    #-- assume the UR1 has a root treatment and a palatal fill.
    #-- user enters UR1 RT P,CO

    #-- what is the current item in ur1pl?
    existing = parent.pt.__dict__[tooth + "pl"]

    parent.pt.__dict__[tooth + "pl"] = properties
    #--update the patient!!
    parent.ui.planChartWidget.setToothProps(tooth, properties)

    #-- new items are input - existing.
    #-- split our string into a list of treatments.
    #-- so UR1 RT P,CO -> [("UR1","RT"),("UR1","P,CO")]
    #-- this also separates off any postsetc..
    #-- and bridge brackets

    existingItems = fee_keys.itemsPerTooth(tooth, existing)
    updatedItems = fee_keys.itemsPerTooth(tooth, properties)

    #check to see if treatments have been removed
    for item in existingItems:
        if item in updatedItems:
            updatedItems.remove(item)
        else:
            #--tooth may be deciduous
            toothname = parent.pt.chartgrid.get(item[0])
            parent.pt.removeFromEstimate(toothname, item[1])
            parent.advise("removing %s from estimate"% item[1])
    #-- so in our exmample, items=[("UR1","RT"),("UR1","P,CO")]
    for item in updatedItems:
        #--ok, so now lookup the four digit itemcode
        ###############################################
        #-- this is critical bit"!!!!!
        #-- if this is incorrect... est will be crap.
        #-- the function returns "4001" - unknown if it is confused by
        #-- the input.
        
        #--tooth may be deciduous
        toothname = parent.pt.chartgrid.get(item[0])
            
        itemcode = fee_keys.getCode(toothname, item[1])
        ###############################################
        #--get a description (for the estimate)
        description = fee_keys.getDescription(itemcode)
        #-- get a fee and pt fee
        fee, ptfee = fee_keys.getItemFees(parent.pt, itemcode)
        #--add to estimate
        parent.pt.addToEstimate(1, itemcode, description, fee, ptfee,
        parent.pt.dnt1, parent.pt.cset, "%s %s"% (toothname, item[1]))

def pass_on_estimate_delete(parent, est):
    '''
    the est has been deleted...
    remove from the plan or completed also?
    '''
    if est.completed == False:
        pl_cmp = "pl"
    else:
        pl_cmp = "cmp"
    
    try:
        spacepos = est.type.index(" ")
        txtype = "%s -%s"% (est.type[:spacepos],est.type[spacepos:])
        print "deleting ", txtype   

        deleteTxItem(parent, pl_cmp, txtype) 
    except ValueError:
        parent.advise ("couldn't pass on delete message - " +
        'badly formed est.type??? %s'% est.type)

def deleteTxItem(parent, pl_cmp, txtype):
    '''
    delete an item
    '''
    tup = txtype.split(" - ")
    try:
        att = tup[0]
        treat = tup[1] + " "
        result = QtGui.QMessageBox.question(parent, "question",
        "remove %s %sfrom this course of treatment?"% (att, treat),
        QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        if result == QtGui.QMessageBox.Yes:
            att = att.lower()
            if re.match("[ul][lr][a-e]", att):
                att = "%s%s"% (att[:2],"abcde".index(att[2])+1)

            if att == "exam":
                parent.pt.examt = ""
                parent.pt.examd = ""
                parent.pt.addHiddenNote("exam", "%s"% tup[1], True)
            else:
                if pl_cmp == "pl":
                    plan = parent.pt.__dict__[att + "pl"].replace(treat, "")
                    parent.pt.__dict__[att + "pl"] = plan
                    completed = parent.pt.__dict__[att + "cmp"]
                    #parent.pt.__dict__[att+"cmp"]=completed
                else:
                    plan = parent.pt.__dict__[att + "pl"]
                    #parent.pt.__dict__[att+"pl"]=plan
                    completed = parent.pt.__dict__[att + "cmp"].replace(
                    treat, "")
                    
                    parent.pt.__dict__[att + "cmp"] = completed
                
                #-- now update the charts
                if re.search("[ul][lr][1-8]", att):
                    parent.updateChartsAfterTreatment(att, plan, completed)

            parent.load_treatTrees()

    except Exception, e:
        parent.advise("Error deleting %s from plan<br>"% txtype +
        "Please remove manually", 1)
        print "handled this in add_tx_to_plan.deleteTxItem", Exception, e

if __name__ == "__main__":
    #-- test code
    localsettings.initiate()
    from openmolar.qt4gui import maingui
    from openmolar.dbtools import patient_class
    app = QtGui.QApplication([])
    mw = maingui.openmolarGui()
    mw.getrecord(11956)
    #disable the functions called
    mw.load_treatTrees = lambda : None
    mw.load_newEstPage = lambda : None
            
    #mw.show()
    xrayAdd(mw)
    