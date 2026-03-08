import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getEmployees } from '../services/api';
import { Users, Mail, Phone, Briefcase } from 'lucide-react';

const Employees = () => {
  const { user } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEmployees();
  }, []);

  const loadEmployees = async () => {
    try {
      const response = await getEmployees();
      setEmployees(response.data);
    } catch (error) {
      console.error('Error loading employees:', error);
    } finally {
      setLoading(false);
    }
  };

  // Look up employee full name by ID
  const getEmployeeName = (id) => {
    const emp = employees.find(e => e.employee_id === id.trim());
    return emp ? `${emp.first_name} ${emp.last_name}` : id;
  };

  // Look up project name — for now just return the ID (replace if you have projects loaded)
  const getProjectLabel = (id) => id.trim();

  const getRoleBadge = (role) => {
    const badges = {
      ceo:      { bg: 'bg-purple-100', text: 'text-purple-800', label: 'CEO' },
      manager:  { bg: 'bg-blue-100',   text: 'text-blue-800',   label: 'Manager' },
      employee: { bg: 'bg-green-100',  text: 'text-green-800',  label: 'Employé' },
    };
    const badge = badges[role] || badges.employee;
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
        {badge.label}
      </span>
    );
  };

  if (loading) {
    return <div className="text-center py-8">Chargement...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Employés</h1>
        <p className="text-gray-600 mt-1">{employees.length} employé(s) accessible(s)</p>
      </div>

      {/* Employees Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {employees.map((employee) => {

          const supervisedList = employee.supervised_employees
            ? employee.supervised_employees.split(';').filter(Boolean)
            : [];

          const projectsList = employee.assigned_projects
            ? employee.assigned_projects.split(';').filter(Boolean)
            : [];

          return (
            <div key={employee.employee_id} className="bg-white rounded-lg shadow hover:shadow-lg transition p-6">
              {/* Header */}
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-gray-900">
                    {employee.first_name} {employee.last_name}
                  </h3>
                  <p className="text-sm text-gray-600">{employee.position}</p>
                </div>
                {getRoleBadge(employee.role)}
              </div>

              {/* Info */}
              <div className="space-y-3">
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <Briefcase className="w-4 h-4" />
                  <span>{employee.department}</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <Mail className="w-4 h-4" />
                  <span className="truncate">{employee.email}</span>
                </div>
                {employee.phone && (
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <Phone className="w-4 h-4" />
                    <span>{employee.phone}</span>
                  </div>
                )}
              </div>

              {/* Projects */}
              {projectsList.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-sm font-medium text-gray-700 mb-2">Projets assignés</p>
                  <div className="flex flex-wrap gap-1">
                    {projectsList.slice(0, 3).map((projectId) => (
                      <span
                        key={projectId}
                        className="px-2 py-1 bg-indigo-50 text-indigo-600 rounded text-xs font-medium"
                      >
                        {getProjectLabel(projectId)}
                      </span>
                    ))}
                    {projectsList.length > 3 && (
                      <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                        +{projectsList.length - 3}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Supervised Employees — show real names */}
              {supervisedList.length > 0 && employee.role !== 'employee' && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Supervise ({supervisedList.length})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {supervisedList.slice(0, 4).map((empId) => (
                      <span
                        key={empId}
                        className="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs font-medium"
                      >
                        {getEmployeeName(empId)}
                      </span>
                    ))}
                    {supervisedList.length > 4 && (
                      <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                        +{supervisedList.length - 4}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Employees;