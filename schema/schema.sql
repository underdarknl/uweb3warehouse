-- MySQL dump 10.13  Distrib 8.0.28, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: warehouse
-- ------------------------------------------------------
-- Server version	8.0.28-0ubuntu0.20.04.3

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `apiuser`
--

DROP TABLE IF EXISTS `apiuser`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `apiuser` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `key` char(32) NOT NULL,
  `active` enum('true','false') NOT NULL DEFAULT 'true',
  `name` varchar(45) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `key_UNIQUE` (`key`),
  UNIQUE KEY `name` (`name`),
  KEY `active` (`active`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `client`
--

DROP TABLE IF EXISTS `client`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `client` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `clientNumber` mediumint unsigned NOT NULL,
  `name` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `city` varchar(45) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `postalCode` varchar(10) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `email` varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `telephone` varchar(30) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  `address` varchar(45) CHARACTER SET utf8 COLLATE utf8_general_ci DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `ID_UNIQUE` (`ID`),
  KEY `clientnumber` (`clientNumber`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `invoice`
--

DROP TABLE IF EXISTS `invoice`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `invoice` (
  `ID` int unsigned NOT NULL AUTO_INCREMENT,
  `sequenceNumber` char(8) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
  `dateCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateDue` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `title` varchar(80) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  `client` mediumint unsigned NOT NULL,
  `status` enum('new','sent','paid') CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  `reservation` tinyint NOT NULL DEFAULT '0',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `sequenceNumber` (`sequenceNumber`),
  KEY `status` (`status`),
  KEY `fk_invoice_1_idx` (`client`),
  CONSTRAINT `fk_invoice_1` FOREIGN KEY (`client`) REFERENCES `client` (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=59 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `invoiceProduct`
--

DROP TABLE IF EXISTS `invoiceProduct`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `invoiceProduct` (
  `ID` int unsigned NOT NULL AUTO_INCREMENT,
  `invoice` int unsigned NOT NULL,
  `product` mediumint unsigned NOT NULL,
  `price` decimal(8,2) NOT NULL,
  `vat_percentage` smallint NOT NULL,
  `name` varchar(45) COLLATE utf8_unicode_ci NOT NULL,
  `quantity` mediumint NOT NULL,
  PRIMARY KEY (`ID`),
  KEY `invoice` (`invoice`),
  KEY `fk_invoiceproduct_1_idx` (`product`),
  CONSTRAINT `fk_invoiceproduct_1` FOREIGN KEY (`product`) REFERENCES `product` (`ID`) ON DELETE RESTRICT,
  CONSTRAINT `product_ibfk_1` FOREIGN KEY (`invoice`) REFERENCES `invoice` (`ID`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb3 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `product`
--

DROP TABLE IF EXISTS `product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `product` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `ean` char(13) DEFAULT NULL,
  `gs1` smallint unsigned DEFAULT NULL,
  `description` text,
  `supplier` tinyint unsigned NOT NULL DEFAULT '1',
  `cost` decimal(6,3) DEFAULT NULL,
  `assemblycosts` decimal(5,3) NOT NULL DEFAULT '0.000',
  `vat` decimal(4,2) NOT NULL DEFAULT '0.00',
  `sku` varchar(45) DEFAULT NULL,
  `dateCreated` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dateDeleted` datetime NOT NULL DEFAULT '1000-01-01 00:00:00',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name_UNIQUE` (`name`,`dateDeleted`),
  UNIQUE KEY `gs1_UNIQUE` (`gs1`,`dateDeleted`),
  UNIQUE KEY `sku_UNIQUE` (`supplier`,`sku`,`dateDeleted`),
  KEY `supplier` (`supplier`),
  CONSTRAINT `supplier` FOREIGN KEY (`supplier`) REFERENCES `supplier` (`ID`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `productpart`
--

DROP TABLE IF EXISTS `productpart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `productpart` (
  `ID` int unsigned NOT NULL AUTO_INCREMENT,
  `product` mediumint unsigned NOT NULL,
  `part` mediumint unsigned DEFAULT NULL,
  `amount` smallint unsigned NOT NULL,
  `assemblycosts` decimal(5,3) NOT NULL DEFAULT '0.000',
  PRIMARY KEY (`ID`),
  KEY `product` (`product`),
  KEY `part` (`part`),
  CONSTRAINT `part` FOREIGN KEY (`part`) REFERENCES `product` (`ID`) ON UPDATE CASCADE,
  CONSTRAINT `product` FOREIGN KEY (`product`) REFERENCES `product` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stock`
--

DROP TABLE IF EXISTS `stock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `product` mediumint unsigned NOT NULL,
  `amount` mediumint NOT NULL,
  `reference` varchar(45) DEFAULT NULL,
  `lot` varchar(45) DEFAULT NULL,
  `dateCreated` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `supplier`
--

DROP TABLE IF EXISTS `supplier`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `supplier` (
  `ID` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(45) NOT NULL,
  `website` varchar(255) DEFAULT NULL,
  `telephone` varchar(45) DEFAULT NULL,
  `contact_person` varchar(255) DEFAULT NULL,
  `email_address` varchar(255) DEFAULT NULL,
  `gscode` varchar(15) DEFAULT NULL,
  `dateDeleted` datetime NOT NULL DEFAULT '1000-01-01 00:00:00',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name_UNIQUE` (`name`,`dateDeleted`)
) ENGINE=InnoDB AUTO_INCREMENT=124 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password` char(100) NOT NULL,
  `active` enum('true','false') NOT NULL DEFAULT 'true',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `email` (`email`),
  KEY `login` (`email`,`password`,`active`),
  KEY `active` (`active`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping events for database 'warehouse'
--

--
-- Dumping routines for database 'warehouse'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2022-05-03 11:45:57
