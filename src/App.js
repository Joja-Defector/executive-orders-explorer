import React, { useState, useEffect } from 'react';
import { Search, Info, Calendar, ChevronDown, ChevronUp, ExternalLink, Filter, Book, AlertCircle } from 'lucide-react';
import Papa from 'papaparse';
import _ from 'lodash';

const App = () => {
  const [executiveOrders, setExecutiveOrders] = useState([]);
  const [filteredOrders, setFilteredOrders] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });
  const [dateRange, setDateRange] = useState({ startDate: '', endDate: '' });
  const [error, setError] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  // Fetch and parse CSV data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Use fetch instead of window.fs.readFile for standard React a
        const basePath = window.location.pathname.includes('executive-orders-explorer') 
          ? '/executive-orders-explorer' 
          : '';
        const response = await fetch(`${basePath}/executive_orders_summarized.csv`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch CSV: ${response.status} ${response.statusText}`);
        }
        
        const text = await response.text();
        
        Papa.parse(text, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
          complete: (results) => {
            if (results.errors && results.errors.length > 0) {
              console.warn("CSV parsing warnings:", results.errors);
            }
            
            // Convert date strings to Date objects for sorting
            const processedData = results.data.map(order => {
              // Handle potential missing data
              if (!order.date) {
                console.warn("Order missing date:", order);
                return { ...order, parsedDate: new Date(0) }; // Default to epoch
              }
              
              try {
                // Parse date in MM/DD/YYYY format
                const dateParts = order.date.split('/');
                const parsedDate = new Date(
                  parseInt(dateParts[2]), // year
                  parseInt(dateParts[0]) - 1, // month (0-indexed)
                  parseInt(dateParts[1]) // day
                );
                
                return {
                  ...order,
                  parsedDate,
                };
              } catch (e) {
                console.error("Error parsing date for order:", order, e);
                return { ...order, parsedDate: new Date(0) }; // Default to epoch
              }
            });
            
            setExecutiveOrders(processedData);
            setFilteredOrders(processedData);
            setIsLoading(false);
          },
          error: (error) => {
            console.error('Error parsing CSV:', error);
            setError('Error parsing CSV file. Please check the file format.');
            setIsLoading(false);
          }
        });
      } catch (error) {
        console.error('Error fetching file:', error);
        setError('Error loading CSV file. Please check if the file exists and is accessible.');
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Filter orders based on search term and date range
  useEffect(() => {
    if (!executiveOrders.length) return;
    
    let filtered = [...executiveOrders];
    
    // Filter by search term
    if (searchTerm) {
      const lowercasedSearch = searchTerm.toLowerCase();
      filtered = filtered.filter(order => 
        (order.title && order.title.toLowerCase().includes(lowercasedSearch)) ||
        (order.content && order.content.toLowerCase().includes(lowercasedSearch)) ||
        (order.summary && order.summary.toLowerCase().includes(lowercasedSearch))
      );
    }
    
    // Filter by date range
    if (dateRange.startDate) {
      const startDate = new Date(dateRange.startDate);
      filtered = filtered.filter(order => order.parsedDate >= startDate);
    }
    
    if (dateRange.endDate) {
      const endDate = new Date(dateRange.endDate);
      filtered = filtered.filter(order => order.parsedDate <= endDate);
    }
    
    // Sort results
    filtered = _.orderBy(
      filtered,
      [sortConfig.key === 'date' ? 'parsedDate' : 'title'],
      [sortConfig.direction]
    );
    
    setFilteredOrders(filtered);
  }, [executiveOrders, searchTerm, dateRange, sortConfig]);

  // Handle sort toggle
  const handleSort = (key) => {
    setSortConfig(prevConfig => ({
      key,
      direction: prevConfig.key === key && prevConfig.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // Handle order selection
  const handleOrderClick = (order) => {
    setSelectedOrder(prev => prev && prev.title === order.title ? null : order);
  };

  // Reset all filters
  const resetFilters = () => {
    setSearchTerm('');
    setDateRange({ startDate: '', endDate: '' });
    setSortConfig({ key: 'date', direction: 'desc' });
    setShowFilters(false);
  };

  // Format date for display (MM/DD/YYYY)
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    
    try {
      const date = new Date(dateStr);
      return `${date.getMonth() + 1}/${date.getDate()}/${date.getFullYear()}`;
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      {/* Header - More modern and attractive */}
      <header className="bg-gradient-to-r from-blue-900 to-blue-700 text-white p-6 shadow-lg">
        <div className="container mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <Book size={28} className="text-blue-200" />
            <h1 className="text-3xl font-bold">Executive Orders Explorer</h1>
          </div>
          <p className="text-blue-100 max-w-2xl">
            Browse and search U.S. Presidential Executive Orders with AI-generated summaries
          </p>
        </div>
      </header>
      
      {/* Main content */}
      <main className="container mx-auto flex-grow p-4 md:p-6">
        {/* Search bar - More prominent and modern */}
        <div className="bg-white rounded-xl shadow-md mb-6 overflow-hidden">
          <div className="p-4 md:p-6">
            <div className="flex flex-col gap-4">
              {/* Main search input */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Search size={20} className="text-gray-400" />
                </div>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search executive orders by title or content..."
                  className="w-full pl-12 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition duration-150"
                />
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                >
                  <Filter 
                    size={20} 
                    className={`${showFilters ? 'text-blue-600' : 'text-gray-400'} hover:text-blue-600 transition-colors duration-150`} 
                  />
                </button>
              </div>
              
              {/* Filters section - collapsible */}
              {showFilters && (
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 animate-fadeIn">
                  <h3 className="font-medium text-gray-700 mb-3">Filter by date range</h3>
                  <div className="flex flex-col sm:flex-row gap-3 items-center">
                    <div className="w-full sm:w-auto flex items-center">
                      <span className="text-gray-500 mr-2 whitespace-nowrap">From:</span>
                      <input
                        type="date"
                        value={dateRange.startDate}
                        onChange={(e) => setDateRange(prev => ({ ...prev, startDate: e.target.value }))}
                        className="flex-grow border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="w-full sm:w-auto flex items-center">
                      <span className="text-gray-500 mr-2 whitespace-nowrap">To:</span>
                      <input
                        type="date"
                        value={dateRange.endDate}
                        onChange={(e) => setDateRange(prev => ({ ...prev, endDate: e.target.value }))}
                        className="flex-grow border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <button 
                      onClick={resetFilters}
                      className="ml-auto bg-white border border-gray-300 hover:bg-gray-100 text-gray-700 font-medium px-4 py-2 rounded-md transition duration-150"
                    >
                      Reset All
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            {/* Results count and sort controls */}
            <div className="flex flex-col sm:flex-row justify-between items-center mt-4 text-sm">
              <div className="mb-2 sm:mb-0 text-gray-600">
                {isLoading ? 'Loading...' : `Displaying ${filteredOrders.length} of ${executiveOrders.length} executive orders`}
              </div>
              <div className="flex gap-4">
                <button 
                  onClick={() => handleSort('title')}
                  className={`flex items-center gap-1 hover:text-blue-700 transition-colors duration-150 ${sortConfig.key === 'title' ? 'font-medium text-blue-700' : 'text-gray-600'}`}
                >
                  Sort by Title
                  {sortConfig.key === 'title' && (
                    sortConfig.direction === 'asc' ? 
                    <ChevronUp size={16} /> : 
                    <ChevronDown size={16} />
                  )}
                </button>
                <button 
                  onClick={() => handleSort('date')}
                  className={`flex items-center gap-1 hover:text-blue-700 transition-colors duration-150 ${sortConfig.key === 'date' ? 'font-medium text-blue-700' : 'text-gray-600'}`}
                >
                  Sort by Date
                  {sortConfig.key === 'date' && (
                    sortConfig.direction === 'asc' ? 
                    <ChevronUp size={16} /> : 
                    <ChevronDown size={16} />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
        
        {/* Loading state - More attractive spinner */}
        {isLoading && (
          <div className="flex flex-col justify-center items-center h-64 bg-white rounded-xl shadow-md">
            <div className="w-16 h-16 border-t-4 border-b-4 border-blue-500 rounded-full animate-spin mb-4"></div>
            <p className="text-gray-600 font-medium">Loading executive orders...</p>
          </div>
        )}
        
        {/* Error state - Better formatting */}
        {error && (
          <div className="text-center py-12 px-4 bg-white rounded-xl shadow-md">
            <AlertCircle size={48} className="mx-auto text-red-500 mb-4" />
            <h2 className="text-xl font-semibold text-gray-700 mb-2">Error Loading Data</h2>
            <p className="text-gray-500 max-w-lg mx-auto mb-6">{error}</p>
            <div className="mt-4 p-5 bg-gray-50 rounded-lg border border-gray-200 max-w-xl mx-auto text-left">
              <p className="font-medium text-gray-800 mb-2">Troubleshooting tips:</p>
              <ul className="list-disc pl-5 space-y-1 text-gray-700">
                <li>Make sure the CSV file is in the public folder</li>
                <li>Verify the file name is exactly: "executive_orders_summarized.csv"</li>
                <li>Check that the CSV has headers: title, date, content, summary, link, page_number</li>
                <li>Ensure dates are in MM/DD/YYYY format</li>
              </ul>
            </div>
          </div>
        )}
        
        {/* No results state - Better formatting */}
        {!isLoading && !error && filteredOrders.length === 0 && (
          <div className="text-center py-16 bg-white rounded-xl shadow-md">
            <Info size={48} className="mx-auto text-gray-400 mb-4" />
            <h2 className="text-xl font-semibold text-gray-700 mb-2">No executive orders found</h2>
            <p className="text-gray-500">Try adjusting your search criteria or filters</p>
            <button 
              onClick={resetFilters}
              className="mt-4 bg-blue-100 hover:bg-blue-200 text-blue-700 font-medium px-4 py-2 rounded-md transition duration-150"
            >
              Reset All Filters
            </button>
          </div>
        )}
        
        {/* Results list - Card-based design with hover effects */}
        {!isLoading && !error && filteredOrders.length > 0 && (
          <div className="space-y-4">
            {filteredOrders.map((order, index) => (
              <div 
                key={index} 
                className={`bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden transition-all duration-200 hover:shadow-md ${selectedOrder && selectedOrder.title === order.title ? 'ring-2 ring-blue-500' : ''}`}
              >
                <div 
                  onClick={() => handleOrderClick(order)}
                  className="cursor-pointer"
                >
                  <div className="p-4 sm:p-5">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
                      <h2 className="text-lg font-medium text-gray-800">{order.title}</h2>
                      <div className="flex items-center text-sm text-gray-500 whitespace-nowrap bg-gray-50 px-3 py-1 rounded-full">
                        <Calendar size={14} className="mr-1.5" />
                        {order.date}
                      </div>
                    </div>
                    
                    {selectedOrder && selectedOrder.title === order.title && (
                      <div className="mt-4 pt-4 border-t border-gray-100 animate-fadeIn">
                        <div className="prose max-w-none text-gray-600">
                          {/* Summary section */}
                          <div className="bg-blue-50 p-4 rounded-lg mb-4">
                            <h3 className="text-sm font-medium text-blue-800 mb-2">AI-Generated Summary</h3>
                            {/* Format summary as markdown with line breaks */}
                            <div className="text-blue-900">
                              {order.summary && order.summary.split('\n').map((line, i) => (
                                <React.Fragment key={i}>
                                  {line}
                                  <br />
                                </React.Fragment>
                              ))}
                            </div>
                          </div>
                          
                          {/* Show original content if available */}
                          {order.content && (
                            <div className="mt-4">
                              <h3 className="text-sm font-medium text-gray-700 mb-2">Original Content</h3>
                              <p className="text-gray-600">{order.content}</p>
                            </div>
                          )}
                        </div>
                        
                        <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between items-center">
                          <a 
                            href={order.link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium"
                          >
                            View Original Document <ExternalLink size={16} className="ml-1" />
                          </a>
                          {order.page_number && (
                            <span className="text-sm text-gray-500">
                              Page {order.page_number}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
      
      {/* Footer - More informative and attractive */}
      <footer className="bg-gray-800 text-white py-6 mt-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <h3 className="text-lg font-medium mb-2">Executive Orders Explorer</h3>
              <p className="text-gray-400 text-sm">
                Data last updated: April 1, 2025
              </p>
            </div>
            <div className="text-sm text-gray-400">
              <p>This tool is for informational purposes only.</p>
              <p>Executive order summaries are AI-generated and may contain inaccuracies.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;