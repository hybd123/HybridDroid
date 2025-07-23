package com.android.commands.monkey.utils;

import java.io.File;
import java.util.*;
import com.android.commands.monkey.events.MonkeyEvent;

public class Tarpit{
    private int tarpitId;
    private String tarpitName;
    private File tarpitScreen;
    private int visitedTimes = 0;
    private List<MonkeyEvent> actions = new ArrayList<>();

    public Tarpit(int tarpitId, List<MonkeyEvent> actions, File tarpitScreen){
        this.tarpitId = tarpitId;
        this.actions = actions;
        this.tarpitScreen = tarpitScreen;
        tarpitName = "Tarpit_" + Integer.toString(tarpitId);
    }

    public void addTarpitActions(MonkeyEvent e){
        actions.add(e);
    }

    public List<MonkeyEvent> getTarpitActions(){
        return actions;
    }

    public int getTarpitId() {
        return tarpitId;
    }

    public File getTarpitScreen() {
        return tarpitScreen;
    }

    public int getVisitedTimes() {
        return visitedTimes;
    }

    public void addVisitedTimes() {
       visitedTimes += 1;
    }

    public String getTarpitName() {
        return tarpitName;
    }

}