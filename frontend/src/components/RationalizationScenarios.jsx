import React, { useState } from 'react';

const RationalizationScenarios = ({ scenarios }) => {
  const [selectedScenario, setSelectedScenario] = useState(0);

  if (!scenarios || scenarios.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">No scenarios available</p>
      </div>
    );
  }

  const scenario = scenarios[selectedScenario];

  const ScenarioComparison = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Before State */}
      <div className="bg-red-50 rounded-lg p-8 border border-red-200">
        <h3 className="text-xl font-bold text-red-900 mb-6">Current State</h3>

        <div className="space-y-4">
          <ComparisonItem
            label="Applications"
            value={scenario.before.app_count}
          />
          <ComparisonItem
            label="Integration Points"
            value={scenario.before.integration_points}
          />
          <ComparisonItem
            label="Database Technologies"
            value={scenario.before.db_technologies}
          />
          <ComparisonItem
            label="Development Teams"
            value={scenario.before.dev_teams}
          />
          <ComparisonItem
            label="Annual Cost"
            value={`€${(scenario.before.cost / 1000000).toFixed(1)}M`}
          />
          <ComparisonItem
            label="Infrastructure Footprint"
            value={`${scenario.before.footprint} units`}
          />
          <ComparisonItem
            label="Cyber Risk"
            value={scenario.before.cyber_risk}
            badge
            badgeColor="bg-red-600"
          />
        </div>
      </div>

      {/* After State */}
      <div className="bg-green-50 rounded-lg p-8 border border-green-200">
        <h3 className="text-xl font-bold text-green-900 mb-6">Target State</h3>

        <div className="space-y-4">
          <ComparisonItem
            label="Applications"
            value={scenario.after.app_count}
          />
          <ComparisonItem
            label="Integration Points"
            value={scenario.after.integration_points}
          />
          <ComparisonItem
            label="Database Technologies"
            value={scenario.after.db_technologies}
          />
          <ComparisonItem
            label="Development Teams"
            value={scenario.after.dev_teams}
          />
          <ComparisonItem
            label="Annual Cost"
            value={`€${(scenario.after.cost / 1000000).toFixed(1)}M`}
          />
          <ComparisonItem
            label="Infrastructure Footprint"
            value={`${scenario.after.footprint} units`}
          />
          <ComparisonItem
            label="Cyber Risk"
            value={scenario.after.cyber_risk}
            badge
            badgeColor="bg-green-600"
          />
        </div>
      </div>
    </div>
  );

  const MetricsDisplay = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-8">
      <MetricCard
        title="Maintenance Reduction"
        value={`€${(scenario.metrics.maintenance_reduction / 1000000).toFixed(1)}M`}
        color="green"
      />
      <MetricCard
        title="Footprint Reduction"
        value={`${scenario.metrics.footprint_reduction_percent.toFixed(1)}%`}
        color="blue"
      />
      <MetricCard
        title="Integration Complexity"
        value={`${scenario.metrics.integration_complexity_reduction.toFixed(1)}%`}
        color="purple"
      />
      <MetricCard
        title="Cyber Risk Reduction"
        value={`${scenario.metrics.cyber_risk_reduction.toFixed(1)}%`}
        color="red"
      />
    </div>
  );

  return (
    <div className="space-y-8">
      {/* Scenario Selector */}
      <div className="flex gap-3 flex-wrap">
        {scenarios.map((s, idx) => (
          <button
            key={idx}
            onClick={() => setSelectedScenario(idx)}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              selectedScenario === idx
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-white text-gray-900 border border-gray-300 hover:border-gray-400'
            }`}
          >
            {s.scenario_name}
          </button>
        ))}
      </div>

      {/* Scenario Details */}
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">
            {scenario.scenario_name}
          </h2>
          <p className="text-gray-600 mt-2">{scenario.description}</p>
          <div className="flex gap-4 mt-4">
            <div>
              <span className="text-sm font-semibold text-gray-600">
                Capability:
              </span>
              <span className="ml-2 text-gray-900 font-semibold">
                {scenario.capability}
              </span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">
                Target ERP:
              </span>
              <span className="ml-2 text-gray-900 font-semibold">
                {scenario.target_erp}
              </span>
            </div>
            <div>
              <span className="text-sm font-semibold text-gray-600">
                Timeline:
              </span>
              <span className="ml-2 text-gray-900 font-semibold">
                {scenario.timeline_months} months
              </span>
            </div>
          </div>
        </div>

        <ScenarioComparison />
        <MetricsDisplay />
      </div>
    </div>
  );
};

const ComparisonItem = ({ label, value, badge, badgeColor }) => (
  <div className="flex justify-between items-center p-3 bg-white rounded border border-gray-100">
    <span className="text-gray-700 font-semibold">{label}</span>
    <span className="text-gray-900 font-bold">
      {badge ? (
        <span className={`${badgeColor} text-white px-3 py-1 rounded-full text-sm`}>
          {value}
        </span>
      ) : (
        value
      )}
    </span>
  </div>
);

const MetricCard = ({ title, value, color }) => {
  const colors = {
    green: 'bg-green-100 text-green-700',
    blue: 'bg-blue-100 text-blue-700',
    purple: 'bg-purple-100 text-purple-700',
    red: 'bg-red-100 text-red-700',
  };

  return (
    <div className={`${colors[color]} rounded-lg p-6 text-center`}>
      <div className="text-sm font-semibold opacity-75 mb-2">{title}</div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  );
};

export default RationalizationScenarios;
