import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import HomePage from './pages/HomePage';
import PlanPage from './pages/PlanPage';
import ProgressPage from './pages/ProgressPage';
import ReportPage from './pages/ReportPage';
import Navigation from './components/Navigation';
import { ResearchProvider } from './context/ResearchContext';
import './App.css';

function App() {
  return (
    <ResearchProvider>
      <Router>
        <div className="min-h-screen gradient-bg">
          <Navigation />
          <main className="container mx-auto px-4 py-8">
            <AnimatePresence mode="wait">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/plan" element={<PlanPage />} />
                <Route path="/progress" element={<ProgressPage />} />
                <Route path="/report" element={<ReportPage />} />
              </Routes>
            </AnimatePresence>
          </main>
        </div>
      </Router>
    </ResearchProvider>
  );
}

export default App;