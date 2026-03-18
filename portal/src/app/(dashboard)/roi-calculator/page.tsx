"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Calculator, TrendingUp, DollarSign, Clock } from "lucide-react";
import { api } from "@/lib/api-client";

interface ROIResult {
  num_students: number;
  current_monthly_cost: number;
  bhapi_monthly_cost: number;
  new_monthly_cost: number;
  monthly_savings: number;
  annual_savings: number;
  roi_percentage: number;
  incident_reduction_pct: number;
  manual_review_reduction_pct: number;
  payback_months: number;
}

export default function ROICalculatorPage() {
  const [numStudents, setNumStudents] = useState(200);
  const [avgIncidents, setAvgIncidents] = useState(5);
  const [costPerIncident, setCostPerIncident] = useState(500);
  const [hoursReview, setHoursReview] = useState(10);
  const [hourlyRate, setHourlyRate] = useState(50);
  const [result, setResult] = useState<ROIResult | null>(null);

  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const data = await api.get<ROIResult>(
          `/api/v1/portal/roi-calculator?num_students=${numStudents}&avg_incidents=${avgIncidents}&cost_per_incident=${costPerIncident}&hours_manual_review=${hoursReview}&hourly_rate=${hourlyRate}`
        );
        setResult(data);
      } catch {
        // Ignore errors during calculation
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [numStudents, avgIncidents, costPerIncident, hoursReview, hourlyRate]);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">ROI Calculator</h1>
        <p className="mt-1 text-sm text-gray-500">
          Estimate the return on investment from deploying Bhapi AI Portal
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Your Organisation" description="Adjust the inputs to match your situation">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Number of students</label>
              <input
                type="range" min={10} max={5000} value={numStudents}
                onChange={(e) => setNumStudents(Number(e.target.value))}
                className="mt-2 w-full"
              />
              <p className="text-right text-sm font-semibold text-primary-700">{numStudents}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">AI incidents per month</label>
              <input
                type="range" min={0} max={50} value={avgIncidents}
                onChange={(e) => setAvgIncidents(Number(e.target.value))}
                className="mt-2 w-full"
              />
              <p className="text-right text-sm font-semibold text-primary-700">{avgIncidents}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Cost per incident ($)</label>
              <input
                type="number" min={0} value={costPerIncident}
                onChange={(e) => setCostPerIncident(Number(e.target.value))}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Hours spent on manual review (weekly)</label>
              <input
                type="number" min={0} value={hoursReview}
                onChange={(e) => setHoursReview(Number(e.target.value))}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Hourly rate ($)</label>
              <input
                type="number" min={0} value={hourlyRate}
                onChange={(e) => setHourlyRate(Number(e.target.value))}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
        </Card>

        {result && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl bg-green-50 p-6 ring-1 ring-green-200">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-green-600" />
                  <span className="text-sm font-medium text-green-800">Annual Savings</span>
                </div>
                <p className="mt-2 text-3xl font-bold text-green-700">
                  ${result.annual_savings.toLocaleString()}
                </p>
              </div>
              <div className="rounded-xl bg-primary-50 p-6 ring-1 ring-primary-200">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary-600" />
                  <span className="text-sm font-medium text-primary-800">ROI</span>
                </div>
                <p className="mt-2 text-3xl font-bold text-primary-700">
                  {result.roi_percentage}%
                </p>
              </div>
            </div>

            <Card title="Cost Comparison">
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Current monthly cost</span>
                  <span className="font-semibold text-gray-900">${result.current_monthly_cost.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Bhapi monthly cost</span>
                  <span className="font-semibold text-primary-700">${result.bhapi_monthly_cost.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">New monthly cost (with Bhapi)</span>
                  <span className="font-semibold text-green-700">${result.new_monthly_cost.toLocaleString()}</span>
                </div>
                <hr className="border-gray-200" />
                <div className="flex justify-between text-sm font-bold">
                  <span className="text-gray-900">Monthly savings</span>
                  <span className="text-green-700">${result.monthly_savings.toLocaleString()}</span>
                </div>
              </div>
            </Card>

            <Card title="Impact Summary">
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">Payback period: <strong>{result.payback_months} months</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <Calculator className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">Incident reduction: <strong>{result.incident_reduction_pct}%</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <Calculator className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">Manual review reduction: <strong>{result.manual_review_reduction_pct}%</strong></span>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
