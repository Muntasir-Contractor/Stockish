import { useEffect, useState } from 'react'
import api from "./components/api.js";
// useState lets you create state variables
  // useEffect lets you run code in response to events, such as when the first compnent renders, or state changes

import './App.css'

function App(){

  // Declare a staste viarable data with initial value null
  // setData is the function used to updata 'data'
  //const {ticker} = useParams(); 
  const [topmovers, setTopMovers] = useState([]);
  console.log(api)

  useEffect(() => {
    api.get("/topmovers")
      .then(res => {
        setTopMovers(res.data);
      })
      .catch(err => {
        console.error(err);
      });
  }, []);
  return (
    <div>
      <div className="Navbar">
        <img className="logo" src="transparent-logo.png" alt="Logo" />
        <nav>
          <ul className="nav_links">
            <li><a href="#">PlaceHolder</a></li>
            <li><a href="#">Second PlaceHolder</a></li>
            <li><a href="#">Third PlaceHolder</a></li>
          </ul>
        </nav>
        <button className="search-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
        </svg>
        </button>
      </div>
      
      <div style={{marginTop: '120px'}}> {/* Add margin to account for fixed navbar */}
        <ul>{topmovers.map(u => (
          <li key={u.symbol}>
            {u.symbol} ({u.name}): ${u.price}USD
            <ul>
              <li>{u.change}, {u.changesPercentage}%</li>
            </ul>
          </li>
        ))}</ul>
      </div>
    </div>
  );
}

export default App
