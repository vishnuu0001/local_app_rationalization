import React from 'react';

const EmptyState = ({ title, description, icon = '📭' }) => {
  return (
    <div className="text-center py-12">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
};

export default EmptyState;
