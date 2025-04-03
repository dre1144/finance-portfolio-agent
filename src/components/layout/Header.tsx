import React from 'react';
import { NotificationCenter } from '../notifications/NotificationCenter';

export const Header: React.FC = () => {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-xl font-semibold">Family Finance</h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <NotificationCenter />
            {/* Другие элементы хедера */}
          </div>
        </div>
      </div>
    </header>
  );
}; 